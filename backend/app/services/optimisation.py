"""Optimisation and Plan Management Service (Phase 4, Tasks P4-6 & P4-7).

Orchestrates Baseline and CP-SAT scheduling runs, executes the IndependentPlanValidator,
manages immutable plan versions and assignments in PostgreSQL, records run manifests,
and logs every operation to the cryptographic audit ledger.
"""
from datetime import datetime, timezone
from typing import Any
import hashlib
import json
import uuid
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.clock import get_clock
from app.core.enums import JobState, PlanKind, PlanSource, PlanStatus, SolverStatus
from app.engines.optimisation.baseline import BaselineScheduler
from app.engines.optimisation.cpsat_solver import CPSATScheduler, CPSATSolverConfig
from app.engines.optimisation.validator import IndependentPlanValidator
from app.models.jobs import Job
from app.models.logistics import MaintenanceRule, Part, ResupplyOrder, SparesInventory
from app.models.operations import MaintenanceRecord, Task, TaskDependency, TaskRequirement
from app.models.plans import ObjectiveWeightSet, Plan, PlanAssignment, PlanValidation, PlanVersion
from app.models.resources import Asset, Personnel, PersonnelQualification, Qualification, Zone
from app.services.audit import write_audit_entry


def load_schedule_snapshot(db: Session) -> dict[str, Any]:
    """Loads a complete relational snapshot required for scheduling and validation."""
    return {
        "tasks": db.execute(select(Task)).scalars().all(),
        "task_requirements": db.execute(select(TaskRequirement)).scalars().all(),
        "task_dependencies": db.execute(select(TaskDependency)).scalars().all(),
        "assets": db.execute(select(Asset)).scalars().all(),
        "personnel": db.execute(select(Personnel)).scalars().all(),
        "personnel_qualifications": db.execute(select(PersonnelQualification)).scalars().all(),
        "maintenance_records": db.execute(select(MaintenanceRecord)).scalars().all(),
        "zones": db.execute(select(Zone)).scalars().all(),
        "spares_inventory": db.execute(select(SparesInventory)).scalars().all(),
    }


def compute_plan_hash(assignments: list[dict[str, Any]], version_num: int) -> str:
    """Computes deterministic SHA-256 digest of schedule assignments."""
    canonical = sorted(
        [
            f"{a['task_id']}:{a.get('asset_id')}:{a['assigned_start'].isoformat()}:{sorted(a.get('personnel_ids') or [])}"
            for a in assignments
        ]
    )
    s = f"v{version_num}:" + "|".join(canonical)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


class OptimisationService:
    """Core service for scheduling, plan versions, and independent validation."""

    def __init__(self, db: Session):
        self.db = db

    def execute_optimisation_job(
        self,
        job_id_str: str,
        job_type: str = "optimise",
        plan_name: str = "Operational Master Plan 2026",
        time_limit_seconds: float = 15.0,
        seed: int = 42,
        weight_set_version: int = 1,
        as_of: datetime | None = None,
        progress_cb: Any = None,
    ) -> dict[str, Any]:
        """Runs baseline heuristic or CP-SAT optimizer, validates with pure-Python validator,

        and persists plan versions, assignments, validations, and audit logs.
        """
        clock_as_of = as_of or get_clock().as_of()

        # 1. Update job to RUNNING
        job_uuid = uuid.UUID(job_id_str)
        job = self.db.execute(select(Job).where(Job.id == job_uuid)).scalars().first()
        if job:
            job.state = JobState.RUNNING.value
            job.progress_percent = 10.0
            job.message = f"Commencing {job_type} scheduling execution"
            self.db.commit()

        if progress_cb:
            progress_cb(10.0, "Loading database resource snapshot...")

        # 2. Load DB snapshot
        snapshot = load_schedule_snapshot(self.db)

        if progress_cb:
            progress_cb(25.0, f"Snapshot loaded ({len(snapshot['tasks'])} tasks, {len(snapshot['assets'])} assets). Dispatching solver...")

        # 3. Fetch Objective Weight Set
        weight_set = (
            self.db.execute(
                select(ObjectiveWeightSet).where(ObjectiveWeightSet.version == weight_set_version)
            )
            .scalars()
            .first()
        )
        delay_w = weight_set.delay_weight if weight_set else 10
        comp_w = weight_set.completion_weight if weight_set else 1000
        churn_w = weight_set.churn_weight if weight_set else 50
        buffer_w = weight_set.buffer_weight if weight_set else 20

        # 4. Execute Solver
        if job_type == "baseline":
            scheduler = BaselineScheduler(slot_minutes=15)
            schedule_result = scheduler.solve(snapshot, as_of=clock_as_of, horizon_days=7)
            plan_kind = PlanKind.BASELINE.value
            plan_source = PlanSource.HEURISTIC.value
            manifest = {
                "scheduler": "Baseline W-EDD Heuristic",
                "slot_minutes": 15,
                "reproducible": True,
            }
        else:
            # Baseline warm-start hint
            if progress_cb:
                progress_cb(40.0, "Generating baseline heuristic warm-start hints...")
            baseline_sol = BaselineScheduler(slot_minutes=15).solve(snapshot, as_of=clock_as_of, horizon_days=7)

            if progress_cb:
                progress_cb(55.0, "Executing OR-Tools CP-SAT discrete solver...")

            def on_cpsat_step(info: dict[str, Any]):
                if progress_cb:
                    pct = min(90.0, 55.0 + info["solution_count"] * 5.0)
                    progress_cb(pct, f"Found CP-SAT solution {info['solution_count']} (obj={info['objective_value']})")

            cfg = CPSATSolverConfig(
                slot_minutes=15,
                time_limit_seconds=time_limit_seconds,
                num_search_workers=1,
                random_seed=seed,
                use_hints=True,
                delay_weight=delay_w,
                completion_weight=comp_w,
                churn_weight=churn_w,
                buffer_weight=buffer_w,
            )
            solver = CPSATScheduler(cfg)
            schedule_result = solver.solve(
                snapshot=snapshot,
                as_of=clock_as_of,
                horizon_days=7,
                baseline_hint=baseline_sol.assignments,
                progress_cb=on_cpsat_step,
            )
            plan_kind = PlanKind.OPTIMISED.value
            plan_source = PlanSource.CPSAT.value
            manifest = schedule_result.manifest

        if progress_cb:
            progress_cb(92.0, "Executing pure-Python independent verification pass...")

        # 5. Independent Pure-Python Validator
        val_result = schedule_result.validation
        if not val_result:
            validator = IndependentPlanValidator()
            val_result = validator.validate_plan(schedule_result.assignments, snapshot)

        # 6. Database Persistence inside transaction
        # Find or create logical Plan
        plan = self.db.execute(select(Plan).where(Plan.name == plan_name)).scalars().first()
        if not plan:
            plan = Plan(name=plan_name)
            self.db.add(plan)
            self.db.flush()

        # Calculate version number
        max_v = self.db.execute(
            select(func.coalesce(func.max(PlanVersion.version_number), 0)).where(PlanVersion.plan_id == plan.id)
        ).scalar_one()
        next_v = max_v + 1

        snap_hash = compute_plan_hash(schedule_result.assignments, next_v)

        # Create PlanVersion
        plan_version = PlanVersion(
            plan_id=plan.id,
            version_number=next_v,
            kind=plan_kind,
            status=PlanStatus.PROPOSED.value,
            based_on_version=max_v if max_v > 0 else None,
            snapshot_hash=snap_hash,
            solver_status=schedule_result.solver_status,
            plan_source=plan_source,
            as_of=clock_as_of,
            metrics_json=schedule_result.metrics,
            solver_runtime_seconds=schedule_result.runtime_seconds,
            run_manifest_json=manifest,
            weight_set_version=weight_set_version,
        )
        self.db.add(plan_version)
        self.db.flush()

        # Proposals remain in PROPOSED status awaiting Reviewer approval (Tasks P5-2, P5-6)

        # Insert Plan Assignments
        for asgn in schedule_result.assignments:
            p_asgn = PlanAssignment(
                plan_version_id=plan_version.id,
                task_id=uuid.UUID(str(asgn["task_id"])),
                asset_id=uuid.UUID(str(asgn["asset_id"])) if asgn.get("asset_id") else None,
                personnel_ids=[uuid.UUID(str(p)) for p in (asgn.get("personnel_ids") or [])],
                assigned_start=asgn["assigned_start"],
                assigned_end=asgn["assigned_end"],
                is_locked=False,
            )
            self.db.add(p_asgn)

        # Insert Plan Validation Record
        plan_val = PlanValidation(
            plan_version_id=plan_version.id,
            is_valid=val_result.is_valid,
            violation_count=val_result.violation_count,
            violations_json=val_result.violations,
            binding_constraints_json=val_result.binding_constraints,
            validated_at=val_result.validated_at,
        )
        self.db.add(plan_val)

        # Record Cryptographic Audit Ledger Entry
        write_audit_entry(
            db=self.db,
            actor_id=None,
            role="system",
            action="GENERATE_PLAN",
            entity_type="plan_versions",
            entity_id=str(plan_version.id),
            reason=f"Generated {job_type} plan version {next_v} with status {schedule_result.solver_status}",
            after_state={
                "plan_id": str(plan.id),
                "version_number": next_v,
                "kind": plan_kind,
                "solver_status": schedule_result.solver_status,
                "is_valid": val_result.is_valid,
                "assignments_count": len(schedule_result.assignments),
                "unassigned_count": len(schedule_result.unassigned_tasks),
                "runtime_seconds": schedule_result.runtime_seconds,
            },
        )

        # Mark Job as COMPLETED
        if job:
            job.state = JobState.COMPLETED.value
            job.progress_percent = 100.0
            job.message = f"Optimisation complete. Status: {schedule_result.solver_status}. Valid: {val_result.is_valid}."
            job.result_id = str(plan_version.id)

        self.db.commit()

        if progress_cb:
            progress_cb(100.0, f"Plan version {next_v} persisted successfully.")

        return {
            "job_id": job_id_str,
            "plan_id": str(plan.id),
            "plan_version_id": str(plan_version.id),
            "version_number": next_v,
            "kind": plan_kind,
            "snapshot_hash": snap_hash,
            "solver_status": schedule_result.solver_status,
            "runtime_seconds": schedule_result.runtime_seconds,
            "is_valid": val_result.is_valid,
            "violation_count": val_result.violation_count,
            "assignments_count": len(schedule_result.assignments),
            "unassigned_count": len(schedule_result.unassigned_tasks),
            "metrics": schedule_result.metrics,
            "manifest": manifest,
        }
