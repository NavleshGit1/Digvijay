import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import PlanKind, PlanSource, PlanStatus, SolverStatus
from app.models.base import BaseModel


class Plan(BaseModel):
    """Logical schedule grouping approved and proposed plan versions (Architecture Section 3.6)."""

    __tablename__ = "plans"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    current_approved_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    versions: Mapped[list["PlanVersion"]] = relationship("PlanVersion", back_populates="plan", cascade="all, delete-orphan")


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

    # Phase 4 additions
    metrics_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    solver_runtime_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    run_manifest_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    constraint_set_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    weight_set_version: Mapped[int | None] = mapped_column(Integer, nullable=True)

    plan: Mapped["Plan"] = relationship("Plan", back_populates="versions")
    assignments: Mapped[list["PlanAssignment"]] = relationship("PlanAssignment", back_populates="plan_version", cascade="all, delete-orphan")
    validation: Mapped["PlanValidation | None"] = relationship("PlanValidation", back_populates="plan_version", uselist=False, cascade="all, delete-orphan")


class PlanAssignment(BaseModel):
    """Specific resource allocations per task inside a plan version."""

    __tablename__ = "plan_assignments"

    plan_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("plan_versions.id"), nullable=False)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    asset_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("assets.id"), nullable=True)
    personnel_ids: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=True)
    assigned_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    assigned_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    plan_version: Mapped["PlanVersion"] = relationship("PlanVersion", back_populates="assignments")


class PlanValidation(BaseModel):
    """Independent verification results evaluating the 10 operational invariants."""

    __tablename__ = "plan_validations"

    plan_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("plan_versions.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    is_valid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    violation_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    violations_json: Mapped[list[dict]] = mapped_column(JSONB, default=list, nullable=False)
    binding_constraints_json: Mapped[list[dict]] = mapped_column(JSONB, default=list, nullable=False)
    validated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    plan_version: Mapped["PlanVersion"] = relationship("PlanVersion", back_populates="validation")


class ObjectiveWeightSet(BaseModel):
    """Versioned multi-objective penalty weights for CP-SAT and Baseline scheduling."""

    __tablename__ = "objective_weight_sets"

    version: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), default="Standard Operational Weights v1", nullable=False)
    delay_weight: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    completion_weight: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)
    churn_weight: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    balance_weight: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    buffer_weight: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
