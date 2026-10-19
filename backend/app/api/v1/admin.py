"""
System Administration and Data Seed Endpoints (Phase 2 Task P2-2).
"""

from datetime import datetime
from typing import Any
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.core.enums import UserRole
from app.engines.data_fusion.generator import seed_database
from app.models.audit import AuditLog
from app.models.identity import User
from app.models.provenance import DataQualityIssue, DatasetVersion

router = APIRouter(prefix="/admin", tags=["Admin"])


class SeedRequest(BaseModel):
    seed: int = Field(default=42, description="Master 64-bit integer seed for deterministic generation")
    as_of: datetime | None = Field(default=None, description="Optional pinned reference time")
    reset: bool = Field(default=True, description="Whether to clear existing domain rows before seeding")


class SeedResponse(BaseModel):
    dataset_hash: str
    seed: int
    version: str = "1.1"
    entity_counts: dict[str, int]
    message: str = "Dataset successfully seeded"


@router.post("/seed", response_model=SeedResponse, status_code=status.HTTP_200_OK)
def trigger_seed(
    request: SeedRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(UserRole.ADMIN)),
) -> SeedResponse:
    """
    Triggers deterministic synthetic data generation and database population.
    Guarantees that identical (seed, as_of) produces the exact same hash byte-for-byte.
    """
    dataset_hash, counts = seed_database(db=db, seed=request.seed, as_of=request.as_of, reset=request.reset)
    return SeedResponse(
        dataset_hash=dataset_hash,
        seed=request.seed,
        version="1.1",
        entity_counts=counts,
        message=f"Seeded {sum(counts.values())} records across {len(counts)} entity tables.",
    )


@router.get("/dataset-versions")
def list_dataset_versions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(UserRole.ADMIN)),
) -> list[dict[str, Any]]:
    """Lists fingerprinted synthetic dataset snapshots."""
    stmt = select(DatasetVersion).order_by(DatasetVersion.created_at.desc())
    versions = db.execute(stmt).scalars().all()
    return [
        {
            "id": str(v.id),
            "version_tag": v.version_tag,
            "generator_version": v.generator_version,
            "seed": v.seed,
            "as_of": v.as_of.isoformat(),
            "content_hash": v.content_hash,
            "entity_counts": v.entity_counts,
            "created_at": v.created_at.isoformat(),
        }
        for v in versions
    ]


@router.get("/data-quality-issues")
def list_data_quality_issues(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(UserRole.ADMIN)),
) -> list[dict[str, Any]]:
    """Lists integrity violations and reconciliation review items."""
    stmt = select(DataQualityIssue).order_by(DataQualityIssue.created_at.desc())
    issues = db.execute(stmt).scalars().all()
    return [
        {
            "id": str(i.id),
            "source_id": str(i.source_id) if i.source_id else None,
            "entity_type": i.entity_type,
            "entity_id": i.entity_id,
            "issue_class": i.issue_class,
            "description": i.description,
            "raw_value": i.raw_value,
            "expected_value": i.expected_value,
            "status": i.status,
            "created_at": i.created_at.isoformat(),
        }
        for i in issues
    ]


@router.get("/audit-logs")
def list_audit_logs(
    action: str | None = None,
    entity_type: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission([UserRole.PLANNER, UserRole.REVIEWER, UserRole.ANALYST, UserRole.ADMIN])),
) -> list[dict[str, Any]]:
    """
    List immutable cryptographic audit ledger entries with SHA-256 hash chains.
    Planners see their own actions; Reviewers, Analysts, and Admins inspect system-wide audit records.
    """
    user_roles = {r.name for r in current_user.roles}
    stmt = select(AuditLog)

    # Scoped access for planner
    if UserRole.ADMIN.value not in user_roles and UserRole.REVIEWER.value not in user_roles and UserRole.ANALYST.value not in user_roles:
        stmt = stmt.where(AuditLog.actor_id == current_user.id)

    if action:
        stmt = stmt.where(AuditLog.action == action)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)

    stmt = stmt.order_by(AuditLog.timestamp.desc()).limit(limit)
    rows = db.execute(stmt).scalars().all()

    return [
        {
            "id": str(row.id),
            "actor_id": str(row.actor_id) if row.actor_id else None,
            "role": row.role,
            "action": row.action,
            "entity_type": row.entity_type,
            "entity_id": row.entity_id,
            "before_state": row.before_state,
            "after_state": row.after_state,
            "plan_version_id": str(row.plan_version_id) if row.plan_version_id else None,
            "reason": row.reason,
            "request_id": row.request_id,
            "timestamp": row.timestamp.isoformat(),
            "previous_hash": row.previous_hash,
            "record_hash": row.record_hash,
        }
        for row in rows
    ]
