"""Plan Governance, Diff Engine, Reviewer Approval & Staleness API (Phase 5).

Implements Architecture Sections 15.1, 15.2, 26.4, and Tasks P5-1, P5-2, P5-7, P5-8, P5-9, P5-10, P5-11.
"""
from typing import Any
import uuid
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, require_permission
from app.core.enums import PlanStatus, UserRole
from app.core.exceptions import ForbiddenException
from app.db.session import get_db
from app.models.identity import User
from app.models.plans import ApprovalRecord, Plan, PlanVersion
from app.services.governance import GovernanceService, calculate_plan_diff

router = APIRouter(tags=["Plan Governance & Lifecycle"])


class ApproveRejectRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=1000, description="Mandatory justification reason")


class RollbackRequest(BaseModel):
    target_version: int = Field(..., description="Target version number to rollback to")
    reason: str = Field(..., min_length=3, max_length=1000, description="Mandatory justification reason for rollback")


class WithdrawRequest(BaseModel):
    reason: str = Field(default="Withdrawn by user", max_length=255)


def require_reviewer_role(current_user: User = Depends(get_current_user)) -> User:
    """Strictly enforces that the user holds the UserRole.REVIEWER role.

    Planners and Administrators without the Reviewer role are strictly blocked with 403 Forbidden.
    """
    user_roles = {r.name for r in current_user.roles}
    if UserRole.REVIEWER.value not in user_roles:
        raise ForbiddenException(
            detail=f"Approval operations strictly require the Reviewer role. Your active roles: {list(user_roles)}."
        )
    return current_user


@router.post("/plans/{plan_id}/versions/{version_number}/approve")
def approve_plan_version(
    plan_id: str,
    version_number: int,
    req: ApproveRejectRequest,
    if_match: str | None = Header(None, alias="If-Match"),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_reviewer_role),
) -> dict[str, Any]:
    """Atomically validates and approves a proposal into the active live plan (Task P5-2, P5-8).

    - Restricted to Reviewers (Admin/Planner blocked with 403).
    - Requires mandatory non-empty reason.
    - Requires optimistic version locking via If-Match header.
    - Idempotency-Key prevents double submission.
    - Runs independent validator against live database snapshot inside transaction (409 on violation).
    - Supersedes current active plan and marks sibling proposals stale in a single atomic transaction.
    """
    try:
        p_uuid = uuid.UUID(plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan UUID format")

    service = GovernanceService(db)
    return service.approve_plan_version(
        plan_id=p_uuid,
        version_number=version_number,
        reviewer=current_user,
        reason=req.reason,
        if_match=if_match,
        idempotency_key=idempotency_key,
    )


@router.post("/plans/{plan_id}/approve")
def approve_plan_alias(
    plan_id: str,
    req: ApproveRejectRequest,
    version: int = Query(..., description="Plan version number to approve"),
    if_match: str | None = Header(None, alias="If-Match"),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_reviewer_role),
) -> dict[str, Any]:
    """Alias for approving a specific plan version."""
    return approve_plan_version(
        plan_id=plan_id,
        version_number=version,
        req=req,
        if_match=if_match,
        idempotency_key=idempotency_key,
        db=db,
        current_user=current_user,
    )


@router.post("/plans/{plan_id}/versions/{version_number}/reject")
def reject_plan_version(
    plan_id: str,
    version_number: int,
    req: ApproveRejectRequest,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_reviewer_role),
) -> dict[str, Any]:
    """Rejects a proposed plan version with mandatory rationale (Task P5-2)."""
    try:
        p_uuid = uuid.UUID(plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan UUID format")

    service = GovernanceService(db)
    return service.reject_plan_version(
        plan_id=p_uuid,
        version_number=version_number,
        reviewer=current_user,
        reason=req.reason,
        idempotency_key=idempotency_key,
    )


@router.post("/plans/{plan_id}/versions/{version_number}/withdraw")
def withdraw_plan_version(
    plan_id: str,
    version_number: int,
    req: WithdrawRequest = WithdrawRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission([UserRole.PLANNER, UserRole.ADMIN])),
) -> dict[str, Any]:
    """Withdraws an unapproved proposed schedule version (Task P5-10)."""
    try:
        p_uuid = uuid.UUID(plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan UUID format")

    service = GovernanceService(db)
    return service.withdraw_plan_version(
        plan_id=p_uuid,
        version_number=version_number,
        user=current_user,
        reason=req.reason,
    )


@router.get("/plans/{plan_id}/versions/{version_number}/diff/{target_version_number}")
def get_plan_versions_diff(
    plan_id: str,
    version_number: int,
    target_version_number: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission([UserRole.PLANNER, UserRole.REVIEWER, UserRole.ANALYST, UserRole.ADMIN])),
) -> dict[str, Any]:
    """Computes fine-grained task and metric differences between two plan versions (Task P5-1, P5-7)."""
    try:
        p_uuid = uuid.UUID(plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan UUID format")

    v_from = (
        db.execute(select(PlanVersion).where(PlanVersion.plan_id == p_uuid, PlanVersion.version_number == target_version_number))
        .scalars()
        .first()
    )
    v_to = (
        db.execute(select(PlanVersion).where(PlanVersion.plan_id == p_uuid, PlanVersion.version_number == version_number))
        .scalars()
        .first()
    )

    if not v_to:
        raise HTTPException(status_code=404, detail=f"Source version {version_number} not found")
    if not v_from:
        raise HTTPException(status_code=404, detail=f"Target comparison version {target_version_number} not found")

    return calculate_plan_diff(db, v_from=v_from, v_to=v_to)


@router.get("/plans/{plan_id}/versions/{version_number}/diff")
def get_plan_diff_against_approved(
    plan_id: str,
    version_number: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission([UserRole.PLANNER, UserRole.REVIEWER, UserRole.ANALYST, UserRole.ADMIN])),
) -> dict[str, Any]:
    """Computes differences between a proposed version and the currently approved plan (Task P5-1)."""
    try:
        p_uuid = uuid.UUID(plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan UUID format")

    plan = db.execute(select(Plan).where(Plan.id == p_uuid)).scalars().first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    v_to = (
        db.execute(select(PlanVersion).where(PlanVersion.plan_id == p_uuid, PlanVersion.version_number == version_number))
        .scalars()
        .first()
    )
    if not v_to:
        raise HTTPException(status_code=404, detail=f"Version {version_number} not found")

    v_from = None
    if plan.current_approved_version_id:
        v_from = (
            db.execute(select(PlanVersion).where(PlanVersion.id == plan.current_approved_version_id))
            .scalars()
            .first()
        )
    elif v_to.based_on_version:
        v_from = (
            db.execute(select(PlanVersion).where(PlanVersion.plan_id == p_uuid, PlanVersion.version_number == v_to.based_on_version))
            .scalars()
            .first()
        )

    return calculate_plan_diff(db, v_from=v_from, v_to=v_to)


@router.get("/plans/{plan_id}/diff")
def get_plan_diff_query(
    plan_id: str,
    target_version: int = Query(2),
    baseline_version: int = Query(1),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission([UserRole.PLANNER, UserRole.REVIEWER, UserRole.ANALYST, UserRole.ADMIN])),
) -> dict[str, Any]:
    """Alias for plan difference calculation via query parameters."""
    return get_plan_versions_diff(
        plan_id=plan_id,
        version_number=target_version,
        target_version_number=baseline_version,
        db=db,
        current_user=current_user,
    )


@router.get("/plans/{plan_id}/versions/{version_number}/staleness")
def get_plan_staleness(
    plan_id: str,
    version_number: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission([UserRole.PLANNER, UserRole.REVIEWER, UserRole.ANALYST, UserRole.ADMIN])),
) -> dict[str, Any]:
    """Checks whether a proposed plan has become stale or invalid against live operational state (Task P5-9)."""
    try:
        p_uuid = uuid.UUID(plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan UUID format")

    service = GovernanceService(db)
    return service.check_plan_staleness(plan_id=p_uuid, version_number=version_number)


@router.post("/plans/{plan_id}/rollback-proposal")
def create_rollback_proposal(
    plan_id: str,
    req: RollbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission([UserRole.PLANNER, UserRole.REVIEWER, UserRole.ADMIN])),
) -> dict[str, Any]:
    """Generates a rollback proposal copying an earlier version's schedule for Reviewer approval (Task P5-11)."""
    try:
        p_uuid = uuid.UUID(plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan UUID format")

    service = GovernanceService(db)
    return service.create_rollback_proposal(
        plan_id=p_uuid,
        target_version_number=req.target_version,
        user=current_user,
        reason=req.reason,
    )


@router.post("/plans/{plan_id}/rollback")
def create_rollback_alias(
    plan_id: str,
    req: RollbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission([UserRole.PLANNER, UserRole.REVIEWER, UserRole.ADMIN])),
) -> dict[str, Any]:
    """Alias for creating a rollback proposal."""
    return create_rollback_proposal(plan_id=plan_id, req=req, db=db, current_user=current_user)


@router.post("/plans/{plan_id}/versions/{version_number}/refresh")
def refresh_plan_version(
    plan_id: str,
    version_number: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission([UserRole.PLANNER, UserRole.ADMIN])),
) -> dict[str, Any]:
    """Warm-start re-solves a schedule proposal against current live snapshot state (Task P5-10)."""
    try:
        p_uuid = uuid.UUID(plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan UUID format")

    service = GovernanceService(db)
    return service.refresh_plan_proposal(
        plan_id=p_uuid,
        version_number=version_number,
        user=current_user,
    )


@router.get("/plans/{plan_id}/approval-records")
def list_approval_records(
    plan_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission([UserRole.PLANNER, UserRole.REVIEWER, UserRole.ANALYST, UserRole.ADMIN])),
) -> list[dict[str, Any]]:
    """Returns the immutable history of all approval and rejection decisions for this plan."""
    try:
        p_uuid = uuid.UUID(plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan UUID format")

    records = (
        db.execute(
            select(ApprovalRecord)
            .options(joinedload(ApprovalRecord.plan_version))
            .where(ApprovalRecord.plan_id == p_uuid)
            .order_by(ApprovalRecord.created_at.desc())
        )
        .unique()
        .scalars()
        .all()
    )

    reviewers = {u.id: u for u in db.execute(select(User)).unique().scalars().all()}

    return [
        {
            "id": str(r.id),
            "plan_id": str(r.plan_id),
            "plan_version_id": str(r.plan_version_id),
            "plan_version_number": r.plan_version.version_number if r.plan_version else None,
            "reviewer_id": str(r.reviewer_id),
            "reviewer_username": reviewers[r.reviewer_id].username if r.reviewer_id in reviewers else "Unknown",
            "decision": r.decision,
            "reason": r.reason,
            "idempotency_key": r.idempotency_key,
            "created_at": r.created_at.isoformat(),
        }
        for r in records
    ]
