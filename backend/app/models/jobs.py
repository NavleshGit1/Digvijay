import uuid
from sqlalchemy import Float, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class Job(BaseModel):
    """Generic asynchronous job registry (Task P1-7 & Section 3)."""

    __tablename__ = "jobs"

    job_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    state: Mapped[str] = mapped_column(String(30), default="queued", index=True, nullable=False)
    progress_percent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    message: Mapped[str | None] = mapped_column(String(255), nullable=True)
    result_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    solver_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    error_details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
