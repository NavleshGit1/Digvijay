"""Plan Governance, Diff Engine, Reviewer Approval & Staleness Service (Phase 5).

Implements Architecture Sections 15.1, 15.2, 26.4, and Tasks P5-1, P5-2, P5-7, P5-8, P5-9, P5-10, P5-11.
"""
from datetime import datetime, timezone
from typing import Any
import uuid
from fastapi import HTTPException, status
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.core.clock import get_clock
from app.core.enums import PlanKind, PlanSource, PlanStatus, SolverStatus, UserRole
from app.core.exceptions import ForbiddenException
from app.engines.optimisation.baseline import BaselineScheduler
from app.engines.optimisation.validator import IndependentPlanValidator, ValidationResult
from app.models.identity import User
from app.models.operations import MaintenanceRecord, Task, TaskDependency, TaskRequirement
from app.models.plans import ApprovalRecord, Plan, PlanAssignment, PlanValidation, PlanVersion
from app.models.resources import Asset, Personnel, PersonnelQualification, Zone
from app.services.audit import write_audit_entry
from app.services.optimisation import compute_plan_hash, load_schedule_snapshot


def calculate_plan_diff(
    db: Session,
    v_from: PlanVersion | None,
    v_to: PlanVersion,
) -> dict[str, Any]:
    """Calculates fine-grained task assignment deltas between two plan versions (Task P5-1, P5-7).

    Compares task scheduling, asset allocations, crew assignments, and objective metrics.
    """
    to_assignments = (
        db.execute(select(PlanAssignment).where(PlanAssignment.plan_version_id == v_to.id))
        .scalars()
        .all()
    )
    from_assignments = (
        db.execute(select(PlanAssignment).where(PlanAssignment.plan_version_id == v_from.id))
        .scalars()
        .all()
        if v_from
        else []
    )

    # Fetch task details for metadata enrichment
    task_ids = list({a.task_id for a in to_assignments} | {a.task_id for a in from_assignments})
    tasks_by_id = {
        t.id: t
        for t in db.execute(select(Task).where(Task.id.in_(task_ids))).scalars().all()
    } if task_ids else {}

    asset_ids = list({a.asset_id for a in to_assignments if a.asset_id} | {a.asset_id for a in from_assignments if a.asset_id})
    assets_by_id = {
        a.id: a
        for a in db.execute(select(Asset).where(Asset.id.in_(asset_ids))).scalars().all()
    } if asset_ids else {}

    from_map: dict[uuid.UUID, PlanAssignment] = {a.task_id: a for a in from_assignments}
    to_map: dict[uuid.UUID, PlanAssignment] = {a.task_id: a for a in to_assignments}

    added = []
    removed = []
    shifted = []
    unchanged = []

    for task_id, to_asgn in to_map.items():
        t = tasks_by_id.get(task_id)
        task_code = t.code if t else "UNKNOWN"
        task_category = t.category if t else "sortie"

        if task_id not in from_map:
            # Newly scheduled task
            a_curr = assets_by_id.get(to_asgn.asset_id) if to_asgn.asset_id else None
            added.append({
                "task_id": str(task_id),
                "task_code": task_code,
                "category": task_category,
                "assigned_start": to_asgn.assigned_start.isoformat(),
                "assigned_end": to_asgn.assigned_end.isoformat(),
                "asset_id": str(to_asgn.asset_id) if to_asgn.asset_id else None,
                "asset_identifier": a_curr.identifier if a_curr else None,
                "personnel_ids": [str(p) for p in (to_asgn.personnel_ids or [])],
                "change_type": "added",
            })
        else:
            # Existing task in both versions -> check for shift / resource change
            from_asgn = from_map[task_id]
            time_shifted = (to_asgn.assigned_start != from_asgn.assigned_start) or (to_asgn.assigned_end != from_asgn.assigned_end)
            asset_changed = to_asgn.asset_id != from_asgn.asset_id
            crew_changed = set(to_asgn.personnel_ids or []) != set(from_asgn.personnel_ids or [])

            if time_shifted or asset_changed or crew_changed:
                start_delta_mins = round((to_asgn.assigned_start - from_asgn.assigned_start).total_seconds() / 60.0, 1)
                end_delta_mins = round((to_asgn.assigned_end - from_asgn.assigned_end).total_seconds() / 60.0, 1)
                a_old = assets_by_id.get(from_asgn.asset_id) if from_asgn.asset_id else None
                a_new = assets_by_id.get(to_asgn.asset_id) if to_asgn.asset_id else None

                shifted.append({
                    "task_id": str(task_id),
                    "task_code": task_code,
                    "category": task_category,
                    "old_start": from_asgn.assigned_start.isoformat(),
                    "new_start": to_asgn.assigned_start.isoformat(),
                    "start_delta_minutes": start_delta_mins,
                    "old_end": from_asgn.assigned_end.isoformat(),
                    "new_end": to_asgn.assigned_end.isoformat(),
                    "end_delta_minutes": end_delta_mins,
                    "old_asset_id": str(from_asgn.asset_id) if from_asgn.asset_id else None,
                    "old_asset_identifier": a_old.identifier if a_old else None,
                    "new_asset_id": str(to_asgn.asset_id) if to_asgn.asset_id else None,
                    "new_asset_identifier": a_new.identifier if a_new else None,
                    "asset_changed": asset_changed,
                    "crew_changed": crew_changed,
                    "change_type": "shifted",
                })
            else:
                unchanged.append({
                    "task_id": str(task_id),
                    "task_code": task_code,
                    "assigned_start": to_asgn.assigned_start.isoformat(),
                    "assigned_end": to_asgn.assigned_end.isoformat(),
                    "asset_id": str(to_asgn.asset_id) if to_asgn.asset_id else None,
                    "change_type": "unchanged",
                })

    for task_id, from_asgn in from_map.items():
        if task_id not in to_map:
            t = tasks_by_id.get(task_id)
            a = assets_by_id.get(from_asgn.asset_id) if from_asgn.asset_id else None
            removed.append({
                "task_id": str(task_id),
                "task_code": t.code if t else "UNKNOWN",
                "assigned_start": from_asgn.assigned_start.isoformat(),
                "assigned_end": from_asgn.assigned_end.isoformat(),
                "asset_id": str(from_asgn.asset_id) if from_asgn.asset_id else None,
                "asset_identifier": a.identifier if a else None,
                "change_type": "removed",
            })

    # Metrics differences
    to_metrics = v_to.metrics_json or {}
    from_metrics = v_from.metrics_json or {} if v_from else {}

    delay_delta = round(float(to_metrics.get("total_delay_minutes", 0.0)) - float(from_metrics.get("total_delay_minutes", 0.0)), 1)
    completion_delta = len(to_assignments) - len(from_assignments)
    runtime_delta = round((v_to.solver_runtime_seconds or 0.0) - (v_from.solver_runtime_seconds or 0.0 if v_from else 0.0), 3)

    return {
        "from_version": v_from.version_number if v_from else None,
        "from_kind": v_from.kind if v_from else None,
        "from_status": v_from.status if v_from else None,
        "to_version": v_to.version_number,
        "to_kind": v_to.kind,
        "to_status": v_to.status,
        "summary": {
            "added_count": len(added),
            "removed_count": len(removed),
            "shifted_count": len(shifted),
            "unchanged_count": len(unchanged),
            "total_assignments_new": len(to_assignments),
            "total_assignments_old": len(from_assignments),
            "churn_count": len(shifted),
        },
        "metrics_diff": {
            "delay_minutes_delta": delay_delta,
            "completion_count_delta": completion_delta,
            "runtime_seconds_delta": runtime_delta,
            "new_total_delay_minutes": to_metrics.get("total_delay_minutes", 0.0),
            "old_total_delay_minutes": from_metrics.get("total_delay_minutes", 0.0),
        },
        "added_assignments": added,
        "removed_assignments": removed,
        "shifted_assignments": shifted,
        "unchanged_assignments": unchanged,
    }


class GovernanceService:
    """Service governing plan lifecycle, approval, revalidation, and rollback."""

    def __init__(self, db: Session):
        self.db = db

    def check_plan_staleness(
        self,
        plan_id: uuid.UUID,
        version_number: int,
    ) -> dict[str, Any]:
        """Evaluates whether a proposed schedule version has become stale (Task P5-9).

        Checks live snapshot hash mismatch, sibling approvals, and invariant violations.
        """
        pv = (
            self.db.execute(
                select(PlanVersion).where(
                    PlanVersion.plan_id == plan_id, PlanVersion.version_number == version_number
                )
            )
            .scalars()
            .first()
        )
        if not pv:
            raise HTTPException(status_code=404, detail="Plan version not found")

        # If already marked stale in database
        if pv.status == PlanStatus.STALE.value:
            return {
                "plan_id": str(plan_id),
                "version_number": version_number,
                "is_stale": True,
                "status": pv.status,
                "reason": pv.stale_reason or "Proposal marked stale by prior approval or schema change",
                "hard_conflict": True,
                "violations": [],
            }

        # Load live database snapshot
        live_snapshot = load_schedule_snapshot(self.db)
        assignments = (
            self.db.execute(select(PlanAssignment).where(PlanAssignment.plan_version_id == pv.id))
            .scalars()
            .all()
        )
        asgn_dicts = [
            {
                "task_id": str(a.task_id),
                "asset_id": str(a.asset_id) if a.asset_id else None,
                "personnel_ids": [str(p) for p in (a.personnel_ids or [])],
                "assigned_start": a.assigned_start,
                "assigned_end": a.assigned_end,
                "is_locked": a.is_locked,
            }
            for a in assignments
        ]

        validator = IndependentPlanValidator()
        val_result = validator.validate_plan(asgn_dicts, live_snapshot)

        is_stale = not val_result.is_valid
        hard_conflict = not val_result.is_valid
        reason = None
        if not val_result.is_valid:
            reason = f"Live operational snapshot conflicts with {len(val_result.violations)} hard constraint violation(s)"

        return {
            "plan_id": str(plan_id),
            "version_number": version_number,
            "is_stale": is_stale,
            "status": pv.status,
            "reason": reason,
            "hard_conflict": hard_conflict,
            "violation_count": len(val_result.violations),
            "violations": val_result.violations,
        }

    def approve_plan_version(
        self,
        plan_id: uuid.UUID,
        version_number: int,
        reviewer: User,
        reason: str,
        if_match: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Atomically validates and approves a proposal into the live active plan (Task P5-2, P5-8).

        Enforces:
        1. Role: Strictly UserRole.REVIEWER (403 for non-reviewers).
        2. Justification: Mandatory non-empty reason.
        3. Concurrency: If-Match header verification (412 on mismatch).
        4. Idempotency: Idempotency-Key deduplication prevents duplicate submissions.
        5. Live Revalidation: Re-evaluates all 10 invariants inside transaction; fails with 409 revalidation_failed.
        6. Single Transaction: Supersedes previous plan, marks siblings stale, updates SQL view, writes approval & audit records.
        """
        # 1. Strictly enforce REVIEWER role
        reviewer_roles = {r.name for r in reviewer.roles}
        if UserRole.REVIEWER.value not in reviewer_roles:
            raise ForbiddenException(
                detail=f"Approval operations strictly require the Reviewer role. Your active roles: {list(reviewer_roles)}."
            )

        # 2. Mandatory justification reason
        clean_reason = reason.strip() if reason else ""
        if len(clean_reason) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mandatory justification reason required to approve a schedule plan version.",
            )

        # Fetch Plan
        plan = self.db.execute(select(Plan).where(Plan.id == plan_id).with_for_update()).scalars().first()
        if not plan:
            raise HTTPException(status_code=404, detail=f"Plan '{plan_id}' not found")

        # Fetch Target PlanVersion
        target_version = (
            self.db.execute(
                select(PlanVersion)
                .where(PlanVersion.plan_id == plan_id, PlanVersion.version_number == version_number)
                .with_for_update()
            )
            .scalars()
            .first()
        )
        if not target_version:
            raise HTTPException(
                status_code=404,
                detail=f"Plan version {version_number} not found for plan {plan_id}",
            )

        # 3. Optimistic Locking (If-Match verification, RFC 7232 Section 3.1)
        if if_match:
            clean_tag = if_match.strip().strip('"').strip("'").lstrip("W/").lstrip("v").strip()
            current_appr_ver = (
                self.db.execute(select(PlanVersion.version_number).where(PlanVersion.id == plan.current_approved_version_id))
                .scalars()
                .first()
            )
            acceptable_tags = {
                str(version_number),
                f"v{version_number}",
            }
            if target_version.based_on_version is not None:
                acceptable_tags.add(str(target_version.based_on_version))
                acceptable_tags.add(f"v{target_version.based_on_version}")
            if current_appr_ver is not None:
                acceptable_tags.add(str(current_appr_ver))
                acceptable_tags.add(f"v{current_appr_ver}")

            if clean_tag not in acceptable_tags and if_match.strip() not in acceptable_tags:
                raise HTTPException(
                    status_code=status.HTTP_412_PRECONDITION_FAILED,
                    detail=f"If-Match precondition failed: Expected version {version_number} or based_on {target_version.based_on_version}, but received '{if_match}'.",
                )

        # 4. Idempotency Key Check
        if idempotency_key:
            existing_record = (
                self.db.execute(
                    select(ApprovalRecord).where(
                        ApprovalRecord.plan_version_id == target_version.id,
                        ApprovalRecord.idempotency_key == idempotency_key,
                    )
                )
                .scalars()
                .first()
            )
            if existing_record:
                return {
                    "idempotent": True,
                    "plan_id": str(plan.id),
                    "version_number": version_number,
                    "status": target_version.status,
                    "decision": existing_record.decision,
                    "reviewer": reviewer.username,
                    "reason": existing_record.reason,
                    "approved_at": existing_record.created_at.isoformat(),
                    "message": "Duplicate approval request returned idempotently",
                }

        # 5. Status Check
        if target_version.status == PlanStatus.APPROVED.value:
            return {
                "idempotent": True,
                "plan_id": str(plan.id),
                "version_number": version_number,
                "status": "approved",
                "decision": "approved",
                "message": "Plan version is already approved",
            }
        if target_version.status == PlanStatus.STALE.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "stale_proposal",
                    "message": f"Cannot approve stale proposal: {target_version.stale_reason or 'Superseded by prior plan'}",
                },
            )
        if target_version.status != PlanStatus.PROPOSED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Only 'proposed' plans can be approved. Current status is '{target_version.status}'.",
            )

        # 6. Approval-time Live Revalidation inside transaction (Architecture Section 26.4)
        live_snapshot = load_schedule_snapshot(self.db)
        assignments = (
            self.db.execute(select(PlanAssignment).where(PlanAssignment.plan_version_id == target_version.id))
            .scalars()
            .all()
        )
        asgn_dicts = [
            {
                "task_id": str(a.task_id),
                "asset_id": str(a.asset_id) if a.asset_id else None,
                "personnel_ids": [str(p) for p in (a.personnel_ids or [])],
                "assigned_start": a.assigned_start,
                "assigned_end": a.assigned_end,
                "is_locked": a.is_locked,
            }
            for a in assignments
        ]

        validator = IndependentPlanValidator()
        val_result = validator.validate_plan(asgn_dicts, live_snapshot)

        if not val_result.is_valid:
            # Mark proposal as stale and abort approval
            target_version.status = PlanStatus.STALE.value
            target_version.stale_reason = f"Revalidation failed: {len(val_result.violations)} constraint violation(s) against live data"
            self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "revalidation_failed",
                    "message": "Approval-time revalidation failed against current operational constraints",
                    "violation_count": len(val_result.violations),
                    "violations": val_result.violations,
                },
            )

        # 7. Single Transaction Atomic Approval
        prev_approved_version_num = None
        if plan.current_approved_version_id:
            prior_approved = (
                self.db.execute(
                    select(PlanVersion).where(PlanVersion.id == plan.current_approved_version_id).with_for_update()
                )
                .scalars()
                .first()
            )
            if prior_approved and prior_approved.id != target_version.id:
                prev_approved_version_num = prior_approved.version_number
                prior_approved.status = PlanStatus.SUPERSEDED.value
                prior_approved.stale_reason = f"Superseded by approval of version {version_number}"

        # Set target version to APPROVED
        target_version.status = PlanStatus.APPROVED.value
        plan.current_approved_version_id = target_version.id

        # Sibling staleness: mark all other proposed versions stale
        sibling_proposals = (
            self.db.execute(
                select(PlanVersion).where(
                    PlanVersion.plan_id == plan_id,
                    PlanVersion.status == PlanStatus.PROPOSED.value,
                    PlanVersion.id != target_version.id,
                )
            )
            .scalars()
            .all()
        )
        stale_count = len(sibling_proposals)
        for sibling in sibling_proposals:
            sibling.status = PlanStatus.STALE.value
            sibling.stale_reason = f"Superseded by approval of sibling version {version_number}"

        # Record in approval_records
        appr_record = ApprovalRecord(
            id=uuid.uuid4(),
            plan_id=plan.id,
            plan_version_id=target_version.id,
            reviewer_id=reviewer.id,
            decision="approved",
            reason=clean_reason,
            idempotency_key=idempotency_key,
        )
        self.db.add(appr_record)

        # Write Cryptographic Audit Ledger Entry
        write_audit_entry(
            db=self.db,
            actor_id=reviewer.id,
            role="reviewer",
            action="APPROVE_PLAN_VERSION",
            entity_type="plan_versions",
            entity_id=str(target_version.id),
            reason=clean_reason,
            plan_version_id=target_version.id,
            before_state={
                "status": "proposed",
                "version_number": version_number,
                "previous_approved_version": prev_approved_version_num,
            },
            after_state={
                "status": "approved",
                "version_number": version_number,
                "plan_id": str(plan.id),
                "siblings_marked_stale": stale_count,
            },
        )

        self.db.commit()

        return {
            "plan_id": str(plan.id),
            "version_number": version_number,
            "status": "approved",
            "decision": "approved",
            "reviewer": reviewer.username,
            "reason": clean_reason,
            "previous_approved_version": prev_approved_version_num,
            "stale_siblings_count": stale_count,
            "approved_at": get_clock().now().isoformat(),
        }

    def reject_plan_version(
        self,
        plan_id: uuid.UUID,
        version_number: int,
        reviewer: User,
        reason: str,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Rejects a proposed schedule plan version with mandatory reviewer rationale (Task P5-2)."""
        # Strictly enforce REVIEWER role
        reviewer_roles = {r.name for r in reviewer.roles}
        if UserRole.REVIEWER.value not in reviewer_roles:
            raise ForbiddenException(
                detail=f"Rejection operations strictly require the Reviewer role. Your active roles: {list(reviewer_roles)}."
            )

        clean_reason = reason.strip() if reason else ""
        if len(clean_reason) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mandatory justification reason required to reject a plan version.",
            )

        target_version = (
            self.db.execute(
                select(PlanVersion).where(
                    PlanVersion.plan_id == plan_id, PlanVersion.version_number == version_number
                )
            )
            .scalars()
            .first()
        )
        if not target_version:
            raise HTTPException(status_code=404, detail="Plan version not found")

        if target_version.status != PlanStatus.PROPOSED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot reject plan version with status '{target_version.status}'. Only 'proposed' plans can be rejected.",
            )

        target_version.status = PlanStatus.REJECTED.value
        target_version.rejection_reason = clean_reason

        # Record in approval_records
        appr_record = ApprovalRecord(
            id=uuid.uuid4(),
            plan_id=plan_id,
            plan_version_id=target_version.id,
            reviewer_id=reviewer.id,
            decision="rejected",
            reason=clean_reason,
            idempotency_key=idempotency_key,
        )
        self.db.add(appr_record)

        # Audit
        write_audit_entry(
            db=self.db,
            actor_id=reviewer.id,
            role="reviewer",
            action="REJECT_PLAN_VERSION",
            entity_type="plan_versions",
            entity_id=str(target_version.id),
            reason=clean_reason,
            plan_version_id=target_version.id,
            before_state={"status": "proposed", "version_number": version_number},
            after_state={"status": "rejected", "version_number": version_number, "reason": clean_reason},
        )
        self.db.commit()

        return {
            "plan_id": str(plan_id),
            "version_number": version_number,
            "status": "rejected",
            "decision": "rejected",
            "reviewer": reviewer.username,
            "reason": clean_reason,
            "rejected_at": get_clock().now().isoformat(),
        }

    def withdraw_plan_version(
        self,
        plan_id: uuid.UUID,
        version_number: int,
        user: User,
        reason: str = "Withdrawn by planner",
    ) -> dict[str, Any]:
        """Allows planners or admins to withdraw an unapproved proposal (Task P5-10)."""
        target_version = (
            self.db.execute(
                select(PlanVersion).where(
                    PlanVersion.plan_id == plan_id, PlanVersion.version_number == version_number
                )
            )
            .scalars()
            .first()
        )
        if not target_version:
            raise HTTPException(status_code=404, detail="Plan version not found")

        if target_version.status != PlanStatus.PROPOSED.value:
            raise HTTPException(
                status_code=400,
                detail=f"Only 'proposed' versions can be withdrawn. Current status is '{target_version.status}'.",
            )

        target_version.status = PlanStatus.WITHDRAWN.value
        target_version.stale_reason = reason

        write_audit_entry(
            db=self.db,
            actor_id=user.id,
            role=user.roles[0].name if user.roles else "planner",
            action="WITHDRAW_PLAN_VERSION",
            entity_type="plan_versions",
            entity_id=str(target_version.id),
            reason=reason,
            plan_version_id=target_version.id,
            before_state={"status": "proposed"},
            after_state={"status": "withdrawn", "reason": reason},
        )
        self.db.commit()

        return {
            "plan_id": str(plan_id),
            "version_number": version_number,
            "status": "withdrawn",
            "reason": reason,
        }

    def create_rollback_proposal(
        self,
        plan_id: uuid.UUID,
        target_version_number: int,
        user: User,
        reason: str,
    ) -> dict[str, Any]:
        """Generates a proposed rollback plan version targeting an earlier approved or superseded schedule (Task P5-11).

        Never silently overwrites. Rollback creates a new proposal for Reviewer inspection and approval.
        """
        clean_reason = reason.strip() if reason else ""
        if len(clean_reason) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mandatory justification reason required to create a rollback proposal.",
            )

        plan = self.db.execute(select(Plan).where(Plan.id == plan_id)).scalars().first()
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")

        # Find target version
        target_v = (
            self.db.execute(
                select(PlanVersion).where(
                    PlanVersion.plan_id == plan_id, PlanVersion.version_number == target_version_number
                )
            )
            .scalars()
            .first()
        )
        if not target_v:
            raise HTTPException(
                status_code=404, detail=f"Target rollback version {target_version_number} not found"
            )

        # Next version number
        max_v = (
            self.db.execute(select(func.coalesce(func.max(PlanVersion.version_number), 0)).where(PlanVersion.plan_id == plan.id))
            .scalar_one()
        )
        new_v = max_v + 1

        # Current approved version number
        curr_approved_num = None
        if plan.current_approved_version_id:
            curr_appr = (
                self.db.execute(select(PlanVersion).where(PlanVersion.id == plan.current_approved_version_id))
                .scalars()
                .first()
            )
            if curr_appr:
                curr_approved_num = curr_appr.version_number

        clock_as_of = get_clock().as_of()

        # Create proposed Rollback PlanVersion
        rollback_pv = PlanVersion(
            plan_id=plan.id,
            version_number=new_v,
            kind=PlanKind.ROLLBACK.value,
            status=PlanStatus.PROPOSED.value,
            based_on_version=curr_approved_num,
            rollback_target=target_version_number,
            snapshot_hash=target_v.snapshot_hash,
            solver_status=target_v.solver_status,
            plan_source=PlanSource.ROLLBACK.value,
            as_of=clock_as_of,
            metrics_json=target_v.metrics_json,
            solver_runtime_seconds=0.01,
            run_manifest_json={
                "rollback_from_version": curr_approved_num,
                "rollback_target_version": target_version_number,
                "requested_by": user.email,
                "reason": clean_reason,
            },
            created_by=user.email,
        )
        self.db.add(rollback_pv)
        self.db.flush()

        # Copy assignments from target version
        target_assignments = (
            self.db.execute(select(PlanAssignment).where(PlanAssignment.plan_version_id == target_v.id))
            .scalars()
            .all()
        )
        new_assignments = []
        for asgn in target_assignments:
            copied = PlanAssignment(
                plan_version_id=rollback_pv.id,
                task_id=asgn.task_id,
                asset_id=asgn.asset_id,
                personnel_ids=asgn.personnel_ids,
                assigned_start=asgn.assigned_start,
                assigned_end=asgn.assigned_end,
                is_locked=asgn.is_locked,
            )
            self.db.add(copied)
            new_assignments.append(copied)

        # Validate against live snapshot
        live_snapshot = load_schedule_snapshot(self.db)
        asgn_dicts = [
            {
                "task_id": str(a.task_id),
                "asset_id": str(a.asset_id) if a.asset_id else None,
                "personnel_ids": [str(p) for p in (a.personnel_ids or [])],
                "assigned_start": a.assigned_start,
                "assigned_end": a.assigned_end,
                "is_locked": a.is_locked,
            }
            for a in new_assignments
        ]
        val_result = IndependentPlanValidator().validate_plan(asgn_dicts, live_snapshot)

        val_rec = PlanValidation(
            plan_version_id=rollback_pv.id,
            is_valid=val_result.is_valid,
            violation_count=val_result.violation_count,
            violations_json=val_result.violations,
            binding_constraints_json=val_result.binding_constraints,
            validated_at=val_result.validated_at,
        )
        self.db.add(val_rec)

        # Audit
        write_audit_entry(
            db=self.db,
            actor_id=user.id,
            role=user.roles[0].name if user.roles else "planner",
            action="CREATE_ROLLBACK_PROPOSAL",
            entity_type="plan_versions",
            entity_id=str(rollback_pv.id),
            reason=clean_reason,
            plan_version_id=rollback_pv.id,
            after_state={
                "version_number": new_v,
                "kind": "rollback",
                "status": "proposed",
                "rollback_target": target_version_number,
                "is_valid": val_result.is_valid,
            },
        )
        self.db.commit()

        return {
            "plan_id": str(plan.id),
            "version_number": new_v,
            "kind": "rollback",
            "status": "proposed",
            "rollback_target": target_version_number,
            "based_on_version": curr_approved_num,
            "is_valid": val_result.is_valid,
            "violation_count": val_result.violation_count,
            "assignments_count": len(new_assignments),
            "reason": clean_reason,
            "created_at": rollback_pv.created_at.isoformat(),
        }

    def refresh_plan_proposal(
        self,
        plan_id: uuid.UUID,
        version_number: int,
        user: User,
    ) -> dict[str, Any]:
        """Creates a fresh warm-started proposal re-solving against current database state (Task P5-10)."""
        plan = self.db.execute(select(Plan).where(Plan.id == plan_id)).scalars().first()
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")

        max_v = (
            self.db.execute(select(func.coalesce(func.max(PlanVersion.version_number), 0)).where(PlanVersion.plan_id == plan.id))
            .scalar_one()
        )
        new_v = max_v + 1
        clock_as_of = get_clock().as_of()

        # Load live DB snapshot and solve baseline W-EDD
        live_snapshot = load_schedule_snapshot(self.db)
        scheduler = BaselineScheduler(slot_minutes=15)
        sched_res = scheduler.solve(live_snapshot, as_of=clock_as_of, horizon_days=7)

        val_result = IndependentPlanValidator().validate_plan(sched_res.assignments, live_snapshot)
        snap_hash = compute_plan_hash(sched_res.assignments, new_v)

        refreshed_pv = PlanVersion(
            plan_id=plan.id,
            version_number=new_v,
            kind=PlanKind.REPLAN.value,
            status=PlanStatus.PROPOSED.value,
            based_on_version=version_number,
            refreshed_from=version_number,
            snapshot_hash=snap_hash,
            solver_status=sched_res.solver_status,
            plan_source=PlanSource.HEURISTIC.value,
            as_of=clock_as_of,
            metrics_json=sched_res.metrics,
            solver_runtime_seconds=sched_res.runtime_seconds,
            run_manifest_json={
                "refreshed_from": version_number,
                "requested_by": user.email,
            },
            created_by=user.email,
        )
        self.db.add(refreshed_pv)
        self.db.flush()

        for asgn in sched_res.assignments:
            p_asgn = PlanAssignment(
                plan_version_id=refreshed_pv.id,
                task_id=uuid.UUID(str(asgn["task_id"])),
                asset_id=uuid.UUID(str(asgn["asset_id"])) if asgn.get("asset_id") else None,
                personnel_ids=[uuid.UUID(str(p)) for p in (asgn.get("personnel_ids") or [])],
                assigned_start=asgn["assigned_start"],
                assigned_end=asgn["assigned_end"],
                is_locked=False,
            )
            self.db.add(p_asgn)

        val_rec = PlanValidation(
            plan_version_id=refreshed_pv.id,
            is_valid=val_result.is_valid,
            violation_count=val_result.violation_count,
            violations_json=val_result.violations,
            binding_constraints_json=val_result.binding_constraints,
            validated_at=val_result.validated_at,
        )
        self.db.add(val_rec)

        write_audit_entry(
            db=self.db,
            actor_id=user.id,
            role=user.roles[0].name if user.roles else "planner",
            action="REFRESH_PLAN_PROPOSAL",
            entity_type="plan_versions",
            entity_id=str(refreshed_pv.id),
            reason=f"Refreshed proposal from version {version_number}",
            plan_version_id=refreshed_pv.id,
            after_state={"version_number": new_v, "refreshed_from": version_number},
        )
        self.db.commit()

        return {
            "plan_id": str(plan.id),
            "version_number": new_v,
            "kind": "replan",
            "status": "proposed",
            "refreshed_from": version_number,
            "is_valid": val_result.is_valid,
            "assignments_count": len(sched_res.assignments),
            "created_at": refreshed_pv.created_at.isoformat(),
        }
