import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import PlanKind, PlanSource, PlanStatus, SolverStatus
from app.models.base import BaseModel


class Plan(BaseModel):
    """Logical schedule grouping approved and proposed plan versions (Architecture Section 3.6)."""

    __tablename__ = "plans"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    current_approved_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    versions: Mapped[list["PlanVersion"]] = relationship("PlanVersion", back_populates="plan")


class PlanVersion(BaseModel):
    """Immutable versioned schedule snapshots (Architecture Section 3.6)."""

    __tablename__ = "plan_versions"

    plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("plans.id"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(50), default=PlanKind.BASELINE.value, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default=PlanStatus.PROPOSED.value, nullable=False)
    based_on_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    solver_status: Mapped[str] = mapped_column(String(50), default=SolverStatus.OPTIMAL.value, nullable=False)
    plan_source: Mapped[str] = mapped_column(String(50), default=PlanSource.CPSAT.value, nullable=False)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    plan: Mapped["Plan"] = relationship("Plan", back_populates="versions")
    assignments: Mapped[list["PlanAssignment"]] = relationship("PlanAssignment", back_populates="plan_version")


class PlanAssignment(BaseModel):
    """Specific resource allocations per task inside a plan version."""

    __tablename__ = "plan_assignments"

    plan_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("plan_versions.id"), nullable=False)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    asset_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("assets.id"), nullable=True)
    personnel_ids: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=True)
    assigned_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    assigned_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    plan_version: Mapped["PlanVersion"] = relationship("PlanVersion", back_populates="assignments")
