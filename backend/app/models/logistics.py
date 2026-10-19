import uuid
from datetime import datetime
from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.clock import get_clock
from app.models.base import BaseModel


class Part(BaseModel):
    """Detailed component and spares catalog definitions (Architecture Section 3.4)."""

    __tablename__ = "parts_catalog"

    part_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(50), index=True, nullable=False)  # avionics, propulsion, hydraulics, airframe
    unit_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)


class SparesInventory(BaseModel):
    """Zone-level spares inventory and stock safety thresholds (Architecture Section 3.4)."""

    __tablename__ = "spares_inventory"

    part_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("parts_catalog.id"), nullable=False)
    zone_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("zones.id"), nullable=False)
    on_hand: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reserved: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    minimum_safety_level: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    part: Mapped["Part"] = relationship("Part")


class MaintenanceRule(BaseModel):
    """Service triggers and inspection thresholds (e.g. 100-hour inspection, overhaul)."""

    __tablename__ = "maintenance_rules"

    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # periodic_inspection, hourly_service, overhaul
    trigger_type: Mapped[str] = mapped_column(String(50), nullable=False)  # flight_hours, cycles, calendar_days
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    tolerance: Mapped[float] = mapped_column(Float, default=0.05, nullable=False)
    estimated_duration_hours: Mapped[float] = mapped_column(Float, default=4.0, nullable=False)


class MaintenancePartRequirement(BaseModel):
    """Join entity defining spare parts required per maintenance rule."""

    __tablename__ = "maintenance_part_requirements"

    rule_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("maintenance_rules.id"), nullable=False)
    part_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("parts_catalog.id"), nullable=False)
    quantity_required: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    rule: Mapped["MaintenanceRule"] = relationship("MaintenanceRule")
    part: Mapped["Part"] = relationship("Part")


class ResupplyOrder(BaseModel):
    """Logistics pipeline resupply orders with lead times (Architecture Section 3.4)."""

    __tablename__ = "resupply_orders"

    part_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("parts_catalog.id"), nullable=False)
    zone_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("zones.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    ordered_at: Mapped[datetime] = mapped_column(default=lambda: get_clock().now(), nullable=False)
    estimated_arrival: Mapped[datetime] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="in_transit", nullable=False)  # pending, in_transit, delivered, cancelled

    part: Mapped["Part"] = relationship("Part")
