from datetime import datetime
from sqlalchemy import DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.clock import get_clock
from app.models.base import BaseModel


class SystemClockState(BaseModel):
    """
    Stores system virtual clock state (Task P1-10 & ADR 0006).
    Enables API and background Celery workers to agree on virtual demo time.
    """

    __tablename__ = "system_clock_state"

    mode: Mapped[str] = mapped_column(String(20), default="system", nullable=False)
    current_as_of: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: get_clock().now(),
        nullable=False,
    )
    time_scale: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
