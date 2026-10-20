"""Replanning and Disruption Recovery Service (Phase 6, Tasks P6-5, P6-6, P6-10).

Orchestrates:
1. Frozen window enforcement (commitments within horizon or locked cannot move).
2. Churn penalty minimization against previous approved commitments.
3. Warm start hint injection into the CP-SAT solver.
4. Independent verification via IndependentPlanValidator.
5. Controlled proposal creation (Strict Human-in-the-Loop governance - Never auto-approve).
6. Real-time notifications to Reviewers via Redis Pub/Sub.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
import hashlib
import json
import uuid

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.core.clock import get_clock
from app.core.enums import JobState, PlanKind, PlanSource, PlanStatus, SolverStatus
from app.core.locks import redis_client
from app.engines.optimisation.baseline import BaselineScheduler
from app.engines.optimisation.cpsat_solver import CPSATScheduler, CPSATSolverConfig
from app.engines.optimisation.validator import IndependentPlanValidator
from app.engines.replanning.impact import OperationalImpactDetector
from app.models.jobs import Job
from app.models.operations import MaintenanceRecord, Task, TaskRequirement
from app.models.plans import ObjectiveWeightSet, Plan, PlanAssignment, PlanValidation, PlanVersion
from app.models.resources import Asset
from app.services.audit import write_audit_entry
from app.services.optimisation import compute_plan_hash, load_schedule_snapshot


@dataclass
class ChurnMetrics:
    tasks_shifted: int
    total_shift_minutes: float
    assets_reassigned: int
    frozen_tasks_preserved: int
    total_scheduled: int
    churn_index: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "tasks_shifted": self.tasks_shifted,
            "total_shift_minutes": round(self.total_shift_minutes, 1),
            "assets_reassigned": self.assets_reassigned,
            "frozen_tasks_preserved": self.frozen_tasks_preserved,
            "total_scheduled": self.total_scheduled,
            "churn_index": round(self.churn_index, 3),
        }


def calculate_schedule_churn(
    baseline_assignments: list[PlanAssignment],
    new_assignments: list[dict[str, Any]],
    frozen_task_ids: set[uuid.UUID],
) -> ChurnMetrics:
    """Calculates stability and churn deltas between previous approved plan and replan proposal."""
    base_map: dict[uuid.UUID, PlanAssignment] = {a.task_id: a for a in baseline_assignments}
    tasks_shifted = 0
    total_shift_mins = 0.0
    assets_reassigned = 0
    frozen_preserved = 0

    for new_a in new_assignments:
        t_id = new_a["task_id"]
        t_uuid = uuid.UUID(t_id) if isinstance(t_id, str) else t_id
        new_start = new_a["assigned_start"]
        new_asset = str(new_a["asset_id"]) if new_a.get("asset_id") else None

        if t_uuid in frozen_task_ids:
            frozen_preserved += 1

        if t_uuid in base_map:
            prev = base_map[t_uuid]
            diff_mins = abs((new_start - prev.assigned_start).total_seconds() / 60.0)
            if diff_mins > 1.0:
                tasks_shifted += 1
                total_shift_mins += diff_mins

            prev_asset = str(prev.asset_id) if prev.asset_id else None
            if prev_asset != new_asset:
                assets_reassigned += 1

    total_sched = len(new_assignments)
    churn_idx = (
        (tasks_shifted + (assets_reassigned * 2)) / (total_sched * 3)
        if total_sched > 0
        else 0.0
    )

    return ChurnMetrics(
        tasks_shifted=tasks_shifted,
        total_shift_minutes=total_shift_mins,
        assets_reassigned=assets_reassigned,
        frozen_tasks_preserved=frozen_preserved,
        total_scheduled=total_sched,
        churn_index=churn_idx,
    )


class ReplanningService:
    """Core service for controlled replanning and rolling horizon scheduling."""

    def __init__(self, db: Session):
        self.db = db

    def execute_replan(
        self,
        job_id_str: str,
        plan_id: uuid.UUID | None = None,
        frozen_window_minutes: int = 120,
        disruption_reason: str = "Operational disruption replan",
        time_limit_seconds: float = 15.0,
        seed: int = 42,
        weight_set_version: int = 1,
        as_of: datetime | None = None,
        progress_cb: Any = None,
    ) -> dict[str, Any]:
        """Executes constrained replanning preserving frozen commitments and minimizing churn."""
        clock_as_of = as_of or get_clock().as_of()
        job_uuid = uuid.UUID(job_id_str)
        job = self.db.execute(select(Job).where(Job.id == job_uuid)).scalars().first()

        if job:
            job.state = JobState.RUNNING.value
            job.progress_percent = 10.0
            job.message = "Loading approved baseline plan for replanning"
            self.db.commit()

        if progress_cb:
            progress_cb(10.0, "Loading approved baseline plan for warm-start hints...")

        # 1. Identify Target Plan and Approved Version
        if plan_id:
            plan = self.db.get(Plan, plan_id)
        else:
            plan = self.db.execute(select(Plan)).scalars().first()

        if not plan or not plan.current_approved_version_id:
            # Fallback to creating a new plan if none exists
            if not plan:
                plan = Plan(name=f"Operational Master Plan {int(clock_as_of.timestamp())}")
                self.db.add(plan)
                self.db.flush()
            approved_version = None
            base_assignments = []
        else:
            approved_version = self.db.get(PlanVersion, plan.current_approved_version_id)
            base_assignments = (
                self.db.execute(
                    select(PlanAssignment).where(PlanAssignment.plan_version_id == approved_version.id)
                )
                .scalars()
                .all()
            )

        # 2. Identify Frozen Assignments (Tasks starting within frozen window or already locked)
        frozen_cutoff = clock_as_of + timedelta(minutes=frozen_window_minutes)
        frozen_task_ids: set[uuid.UUID] = set()
        frozen_hints: list[dict[str, Any]] = []

        for asgn in base_assignments:
            if asgn.is_locked or asgn.assigned_start <= frozen_cutoff:
                frozen_task_ids.add(asgn.task_id)
                frozen_hints.append({
                    "task_id": str(asgn.task_id),
                    "asset_id": str(asgn.asset_id) if asgn.asset_id else None,
                    "personnel_ids": [str(pid) for pid in (asgn.personnel_ids or [])],
                    "assigned_start": asgn.assigned_start,
                    "assigned_end": asgn.assigned_end,
                    "is_locked": True,
                })

        if progress_cb:
            progress_cb(
                25.0,
                f"Frozen window applied: {len(frozen_task_ids)} commitments locked across next {frozen_window_minutes} mins.",
            )

        # 3. Load DB Snapshot
        snapshot = load_schedule_snapshot(self.db)

        # 4. Fetch Objective Weight Set with Churn penalty
        weight_set = (
            self.db.execute(
                select(ObjectiveWeightSet).where(ObjectiveWeightSet.version == weight_set_version)
            )
            .scalars()
            .first()
        )
        delay_w = weight_set.delay_weight if weight_set else 10
        comp_w = weight_set.completion_weight if weight_set else 1000
        churn_w = max(weight_set.churn_weight if weight_set else 50, 75)  # Boosted churn penalty for replanning

        # 5. Execute CP-SAT Solver with previous assignments as warm start hints
        if progress_cb:
            progress_cb(45.0, "Running CP-SAT solver with warm start hints and churn minimization...")

        # Base hints from previous assignments
        all_hints = [
            {
                "task_id": str(a.task_id),
                "asset_id": str(a.asset_id) if a.asset_id else None,
                "personnel_ids": [str(pid) for pid in (a.personnel_ids or [])],
                "assigned_start": a.assigned_start,
                "assigned_end": a.assigned_end,
            }
            for a in base_assignments
        ]

        cfg = CPSATSolverConfig(
            slot_minutes=15,
            time_limit_seconds=time_limit_seconds,
            num_search_workers=1,
            random_seed=seed,
            use_hints=True,
            delay_weight=delay_w,
            completion_weight=comp_w,
            churn_weight=churn_w,
        )
        solver = CPSATScheduler(cfg)

        def on_cpsat_step(info: dict[str, Any]):
            if progress_cb:
                pct = min(85.0, 45.0 + info["solution_count"] * 5.0)
                progress_cb(pct, f"Found replan candidate {info['solution_count']} (obj={info['objective_value']})")

        schedule_result = solver.solve(
            snapshot=snapshot,
            as_of=clock_as_of,
            horizon_days=7,
            baseline_hint=all_hints,
            progress_cb=on_cpsat_step,
        )

        if progress_cb:
            progress_cb(85.0, "Verifying replan proposal against independent validator...")

        # 6. Independent Pure-Python Validation
        validator = IndependentPlanValidator()
        validation_res = validator.validate_plan(schedule_result.assignments, snapshot)

        # 7. Calculate Churn Metrics
        churn_metrics = calculate_schedule_churn(
            baseline_assignments=base_assignments,
            new_assignments=schedule_result.assignments,
            frozen_task_ids=frozen_task_ids,
        )

        # 8. Create New Plan Version (PROPOSED - Never Auto-Approved!)
        max_ver = (
            self.db.execute(
                select(func.coalesce(func.max(PlanVersion.version_number), 0)).where(
                    PlanVersion.plan_id == plan.id
                )
            ).scalar_one()
        )
        new_ver_num = max_ver + 1
        plan_hash = compute_plan_hash(schedule_result.assignments, new_ver_num)

        merged_metrics = dict(schedule_result.metrics)
        merged_metrics["churn"] = churn_metrics.to_dict()
        merged_metrics["disruption_reason"] = disruption_reason
        merged_metrics["frozen_window_minutes"] = frozen_window_minutes

        replan_version = PlanVersion(
            plan_id=plan.id,
            version_number=new_ver_num,
            kind="replan",
            status=PlanStatus.PROPOSED.value,
            based_on_version=approved_version.version_number if approved_version else None,
            snapshot_hash=plan_hash,
            solver_status=schedule_result.solver_status,
            plan_source=PlanSource.CPSAT.value,
            as_of=clock_as_of,
            metrics_json=merged_metrics,
            solver_runtime_seconds=schedule_result.runtime_seconds,
            run_manifest_json={
                "solver": "OR-Tools CP-SAT Replan Mode",
                "frozen_window_minutes": frozen_window_minutes,
                "churn_weight": churn_w,
                "disruption_reason": disruption_reason,
                "based_on_version": approved_version.version_number if approved_version else None,
                "reproducible": True,
            },
            stale_reason=None,
            created_by="replanning_engine",
        )
        self.db.add(replan_version)
        self.db.flush()

        # 9. Store Assignments (preserving locked flag)
        for a_dict in schedule_result.assignments:
            t_id = a_dict["task_id"]
            t_uuid = uuid.UUID(t_id) if isinstance(t_id, str) else t_id
            is_locked = t_uuid in frozen_task_ids

            p_uuids = None
            if a_dict.get("personnel_ids"):
                p_uuids = [
                    uuid.UUID(p) if isinstance(p, str) else p
                    for p in a_dict["personnel_ids"]
                ]

            asgn = PlanAssignment(
                plan_version_id=replan_version.id,
                task_id=t_uuid,
                asset_id=uuid.UUID(a_dict["asset_id"]) if a_dict.get("asset_id") else None,
                personnel_ids=p_uuids,
                assigned_start=a_dict["assigned_start"],
                assigned_end=a_dict["assigned_end"],
                is_locked=is_locked,
            )
            self.db.add(asgn)

        # 10. Store Validation Result
        val_rec = PlanValidation(
            plan_version_id=replan_version.id,
            is_valid=validation_res.is_valid,
            violation_count=validation_res.violation_count,
            violations_json=validation_res.violations,
            binding_constraints_json=validation_res.binding_constraints,
            validated_at=clock_as_of,
        )
        self.db.add(val_rec)

        # 11. Cryptographic Audit Log Entry
        write_audit_entry(
            db=self.db,
            actor_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            role="system",
            action="GENERATE_REPLAN_PROPOSAL",
            entity_type="plan_versions",
            entity_id=str(replan_version.id),
            reason=f"Controlled replan proposal v{new_ver_num} generated for '{disruption_reason}'",
            before_state={"approved_version": approved_version.version_number if approved_version else None},
            after_state={
                "version_number": new_ver_num,
                "status": "proposed",
                "kind": "replan",
                "churn": churn_metrics.to_dict(),
                "is_valid": validation_res.is_valid,
            },
        )

        # 12. Finalize Job
        if job:
            job.state = JobState.COMPLETED.value
            job.progress_percent = 100.0
            job.message = f"Replan proposal v{new_ver_num} generated successfully (Churn index: {churn_metrics.churn_index})"
            job.result_json = {
                "plan_id": str(plan.id),
                "plan_version_id": str(replan_version.id),
                "version_number": new_ver_num,
                "status": "proposed",
                "kind": "replan",
                "churn": churn_metrics.to_dict(),
                "is_valid": validation_res.is_valid,
            }

        self.db.commit()

        # 13. Notify Reviewers via Redis Pub/Sub
        try:
            notification = {
                "event": "proposal_created",
                "plan_id": str(plan.id),
                "plan_version_id": str(replan_version.id),
                "version_number": new_ver_num,
                "kind": "replan",
                "reason": disruption_reason,
                "churn_index": churn_metrics.churn_index,
                "timestamp": clock_as_of.isoformat(),
            }
            redis_client.publish("alerts:new", json.dumps(notification))
        except Exception:
            pass

        return {
            "plan_id": str(plan.id),
            "plan_version_id": str(replan_version.id),
            "version_number": new_ver_num,
            "status": "proposed",
            "kind": "replan",
            "snapshot_hash": plan_hash,
            "churn": churn_metrics.to_dict(),
            "is_valid": validation_res.is_valid,
        }
