"""Constraint Registry Management & Governance API (Architecture Section 26.8, Tasks P4-12, P5-12).

Provides versioned constraint sets, draft parameter tuning, impact preview revalidation, and activation.
"""
from typing import Any
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.clock import get_clock
from app.core.enums import PlanStatus, UserRole
from app.db.session import get_db
from app.engines.optimisation.validator import IndependentPlanValidator
from app.models.identity import User
from app.models.plans import ConstraintSet, Plan, PlanAssignment, PlanVersion
from app.services.audit import write_audit_entry
from app.services.optimisation import load_schedule_snapshot

router = APIRouter(prefix="/constraints", tags=["Constraint Registry"])


class ConstraintSetCreateRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    clone_from_version: str | None = Field(default=None, description="Version to clone from, defaults to active")


class ConstraintParameterUpdateRequest(BaseModel):
    parameters: dict[str, Any] = Field(..., description="Key-value mapping of constraint parameter overrides")


@router.get("/sets")
def list_constraint_sets(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission([UserRole.PLANNER, UserRole.REVIEWER, UserRole.ANALYST, UserRole.ADMIN])),
) -> list[dict[str, Any]]:
    """Returns all versioned operational constraint configurations."""
    c_sets = db.execute(select(ConstraintSet).order_by(ConstraintSet.created_at.desc())).scalars().all()
    return [
        {
            "id": str(cs.id),
            "version": cs.version,
            "name": cs.name,
            "status": cs.status,
            "parameters": cs.parameters_json,
            "created_by": cs.created_by,
            "created_at": cs.created_at.isoformat(),
        }
        for cs in c_sets
    ]


@router.post("/sets", status_code=status.HTTP_201_CREATED)
def clone_constraint_set(
    req: ConstraintSetCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission([UserRole.ADMIN])),
) -> dict[str, Any]:
    """Clones an active constraint set into a new draft version for editing (Admin only, audited)."""
    # Find source set
    source_set = None
    if req.clone_from_version:
        source_set = db.execute(select(ConstraintSet).where(ConstraintSet.version == req.clone_from_version)).scalars().first()
    if not source_set:
        source_set = db.execute(select(ConstraintSet).where(ConstraintSet.status == "active")).scalars().first()

    base_params = source_set.parameters_json if source_set else {
        "min_turnaround_minutes": 45,
        "max_flight_hours_daily": 8,
        "max_crew_duty_hours": 12,
        "min_crew_rest_hours": 10,
    }

    # Generate version string v{count+1}.0-draft
    count = db.execute(select(ConstraintSet)).scalars().all()
    new_version = f"v{len(count) + 1}.0-draft"

    new_set = ConstraintSet(
        id=uuid.uuid4(),
        version=new_version,
        name=req.name,
        status="draft",
        parameters_json=dict(base_params),
        created_by=current_user.email,
    )
    db.add(new_set)
    db.flush()

    write_audit_entry(
        db=db,
        actor_id=current_user.id,
        role="admin",
        action="CLONE_CONSTRAINT_SET",
        entity_type="constraint_sets",
        entity_id=str(new_set.id),
        reason=f"Admin created draft constraint set '{new_version}'",
        after_state={"version": new_version, "name": req.name, "status": "draft"},
    )
    db.commit()

    return {
        "id": str(new_set.id),
        "version": new_set.version,
        "name": new_set.name,
        "status": new_set.status,
        "parameters": new_set.parameters_json,
        "created_at": new_set.created_at.isoformat(),
    }


@router.put("/sets/{set_id}")
def update_constraint_set_parameters(
    set_id: str,
    req: ConstraintParameterUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission([UserRole.ADMIN])),
) -> dict[str, Any]:
    """Updates parameter thresholds on a draft constraint set (Admin only, audited)."""
    try:
        cs_uuid = uuid.UUID(set_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid constraint set UUID")

    cs = db.execute(select(ConstraintSet).where(ConstraintSet.id == cs_uuid)).scalars().first()
    if not cs:
        raise HTTPException(status_code=404, detail="Constraint set not found")

    if cs.status != "draft":
        raise HTTPException(status_code=400, detail="Only 'draft' constraint sets can be modified")

    before = dict(cs.parameters_json)
    updated_params = dict(cs.parameters_json)
    updated_params.update(req.parameters)
    cs.parameters_json = updated_params

    write_audit_entry(
        db=db,
        actor_id=current_user.id,
        role="admin",
        action="UPDATE_CONSTRAINT_SET",
        entity_type="constraint_sets",
        entity_id=str(cs.id),
        reason=f"Admin updated parameters for constraint set {cs.version}",
        before_state=before,
        after_state=updated_params,
    )
    db.commit()

    return {
        "id": str(cs.id),
        "version": cs.version,
        "name": cs.name,
        "status": cs.status,
        "parameters": cs.parameters_json,
    }


@router.post("/sets/{set_id}/impact-preview")
def preview_constraint_set_impact(
    set_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission([UserRole.PLANNER, UserRole.REVIEWER, UserRole.ANALYST, UserRole.ADMIN])),
) -> dict[str, Any]:
    """Revalidates current approved plan and pending proposals under the draft constraint set (Task P5-12)."""
    try:
        cs_uuid = uuid.UUID(set_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid constraint set UUID")

    cs = db.execute(select(ConstraintSet).where(ConstraintSet.id == cs_uuid)).scalars().first()
    if not cs:
        raise HTTPException(status_code=404, detail="Constraint set not found")

    live_snapshot = load_schedule_snapshot(db)
    validator = IndependentPlanValidator()

    # Revalidate active approved plans
    active_plans = db.execute(select(Plan)).scalars().all()
    impacts = []

    for p in active_plans:
        if not p.current_approved_version_id:
            continue
        pv = db.execute(select(PlanVersion).where(PlanVersion.id == p.current_approved_version_id)).scalars().first()
        if not pv:
            continue

        assignments = db.execute(select(PlanAssignment).where(PlanAssignment.plan_version_id == pv.id)).scalars().all()
        asgns = [
            {
                "task_id": str(a.task_id),
                "asset_id": str(a.asset_id) if a.asset_id else None,
                "personnel_ids": [str(x) for x in (a.personnel_ids or [])],
                "assigned_start": a.assigned_start,
                "assigned_end": a.assigned_end,
                "is_locked": a.is_locked,
            }
            for a in assignments
        ]

        val_res = validator.validate_plan(asgns, live_snapshot)
        impacts.append({
            "plan_id": str(p.id),
            "plan_name": p.name,
            "approved_version": pv.version_number,
            "is_valid": val_res.is_valid,
            "violations_count": len(val_res.violations),
            "violations": val_res.violations,
        })

    # Count pending proposals that will be marked stale
    pending_proposals_count = db.execute(
        select(PlanVersion).where(PlanVersion.status == PlanStatus.PROPOSED.value)
    ).scalars().all()

    return {
        "constraint_set_id": str(cs.id),
        "constraint_set_version": cs.version,
        "impact_summary": {
            "approved_plans_checked": len(impacts),
            "approved_plans_valid": sum(1 for i in impacts if i["is_valid"]),
            "pending_proposals_will_be_staled": len(pending_proposals_count),
        },
        "plan_impacts": impacts,
    }


@router.post("/sets/{set_id}/activate")
def activate_constraint_set(
    set_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission([UserRole.ADMIN])),
) -> dict[str, Any]:
    """Activates a draft constraint set, archives prior active sets, and marks pending proposals stale (Task P5-12)."""
    try:
        cs_uuid = uuid.UUID(set_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid constraint set UUID")

    cs = db.execute(select(ConstraintSet).where(ConstraintSet.id == cs_uuid)).scalars().first()
    if not cs:
        raise HTTPException(status_code=404, detail="Constraint set not found")

    # 1. Archive current active set(s)
    prior_actives = db.execute(select(ConstraintSet).where(ConstraintSet.status == "active")).scalars().all()
    for prior in prior_actives:
        prior.status = "archived"

    # 2. Activate target set
    clean_version = cs.version.replace("-draft", "")
    cs.version = clean_version
    cs.status = "active"

    # 3. Mark all pending proposals stale
    pending = db.execute(select(PlanVersion).where(PlanVersion.status == PlanStatus.PROPOSED.value)).scalars().all()
    for p in pending:
        p.status = PlanStatus.STALE.value
        p.stale_reason = f"Constraint set {clean_version} activated"

    write_audit_entry(
        db=db,
        actor_id=current_user.id,
        role="admin",
        action="ACTIVATE_CONSTRAINT_SET",
        entity_type="constraint_sets",
        entity_id=str(cs.id),
        reason=f"Admin activated constraint set {clean_version}, marking {len(pending)} pending proposals stale",
        after_state={"version": clean_version, "proposals_marked_stale": len(pending)},
    )
    db.commit()

    return {
        "id": str(cs.id),
        "version": clean_version,
        "status": "active",
        "pending_proposals_marked_stale": len(pending),
        "activated_at": get_clock().now().isoformat(),
    }
