import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.clock import get_clock
from app.core.enums import TaskPriority, TaskStatus
from app.models.base import BaseModel


class Task(BaseModel):
    """Operational task work items (Sortie, Patrol, Ferry, Inspection) (Architecture Section 3.5)."""

    __tablename__ = "tasks"

    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(50), index=True, nullable=False)  # patrol_sortie, maintenance_inspection, ferry_transit, logistics_airdrop, readiness_drill
    zone_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("zones.id"), nullable=False)
    earliest_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    latest_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    priority: Mapped[str] = mapped_column(String(50), default=TaskPriority.ROUTINE.value, index=True, nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default=TaskStatus.PENDING.value, index=True, nullable=False)

    requirements: Mapped[list["TaskRequirement"]] = relationship("TaskRequirement", back_populates="task")
    successors: Mapped[list["TaskDependency"]] = relationship("TaskDependency", foreign_keys="TaskDependency.predecessor_id", back_populates="predecessor")
    predecessors: Mapped[list["TaskDependency"]] = relationship("TaskDependency", foreign_keys="TaskDependency.successor_id", back_populates="successor")


class TaskRequirement(BaseModel):
    """Resource specifications required for a task (asset type, headcount, qualifications)."""

    __tablename__ = "task_requirements"

    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    asset_type_required: Mapped[str] = mapped_column(String(50), nullable=False)
    crew_headcount: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    required_qualification_code: Mapped[str | None] = mapped_column(String(50), nullable=True)

    task: Mapped["Task"] = relationship("Task", back_populates="requirements")


class TaskDependency(BaseModel):
    """Directed precedence dependency between tasks (guaranteed acyclic DAG)."""

    __tablename__ = "task_dependencies"

    predecessor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    successor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    min_lag_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    predecessor: Mapped["Task"] = relationship("Task", foreign_keys=[predecessor_id], back_populates="successors")
    successor: Mapped["Task"] = relationship("Task", foreign_keys=[successor_id], back_populates="predecessors")


class TaskExecution(BaseModel):
    """Historical realized execution metrics for model training and verification."""

    __tablename__ = "task_executions"

    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    plan_version_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    assignment_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    actual_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actual_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    delay_minutes: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_disrupted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    task: Mapped["Task"] = relationship("Task")


class MaintenanceRecord(BaseModel):
    """Work orders and maintenance executions on aircraft assets."""

    __tablename__ = "maintenance_records"

    asset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("assets.id"), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # periodic_inspection, 100_hour, overhaul, unscheduled_repair
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    predicted_completion: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_unplanned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="scheduled", nullable=False)  # scheduled, in_progress, completed, deferred
