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
