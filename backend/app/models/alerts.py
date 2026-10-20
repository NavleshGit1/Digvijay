import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.clock import get_clock
from app.models.base import BaseModel


class AlertRule(BaseModel):
    """Configuration catalogue of operational alert rules and thresholds (Architecture Section 26.7)."""

    __tablename__ = "alert_rules"

    rule_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)  # critical, high, medium, low
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    threshold_value: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    hysteresis_buffer: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    scope: Mapped[str] = mapped_column(String(50), default="global", nullable=False)  # global, zone, asset, logistics, plan
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Alert(BaseModel):
    """Operational alert instances with deduplication, anti-flapping, and lifecycle state."""

    __tablename__ = "alerts"

    rule_code: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="medium", index=True, nullable=False)  # critical, high, medium, low
    status: Mapped[str] = mapped_column(String(20), default="new", index=True, nullable=False)  # new, acknowledged, resolved
    dedup_key: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)  # asset, task, maintenance, plan, system
    entity_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: get_clock().now(), nullable=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: get_clock().now(), nullable=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
