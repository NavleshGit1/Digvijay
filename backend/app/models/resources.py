import uuid
from datetime import datetime
from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.clock import get_clock
from app.core.enums import AssetStatus, AssetType, PersonnelStatus
from app.models.base import BaseModel


class Zone(BaseModel):
    """Fictional airbases, operating sectors, and bays (Architecture Section 3.3)."""

    __tablename__ = "zones"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    capacity_limit: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    coordinates_geojson: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    assets: Mapped[list["Asset"]] = relationship("Asset", back_populates="zone")
    personnel: Mapped[list["Personnel"]] = relationship("Personnel", back_populates="home_zone")


class Asset(BaseModel):
    """Operational aircraft, equipment, and critical airframes (Architecture Section 3.3)."""

    __tablename__ = "assets"

    identifier: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    asset_type: Mapped[str] = mapped_column(String(50), default=AssetType.FIGHTER_MULTIROLE.value, index=True, nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default=AssetStatus.AVAILABLE.value, index=True, nullable=False)
    health_score: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    zone_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("zones.id"), nullable=False)
    current_location: Mapped[str | None] = mapped_column(String(100), nullable=True)
    flight_hours: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    cycles: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    zone: Mapped["Zone"] = relationship("Zone", back_populates="assets")


class Personnel(BaseModel):
    """Flight crew, weapons operators, and maintenance technicians (Architecture Section 3.3)."""

    __tablename__ = "personnel"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    callsign: Mapped[str | None] = mapped_column(String(50), nullable=True)
    role_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)  # pilot, maintenance_tech, wso
    status: Mapped[str] = mapped_column(String(50), default=PersonnelStatus.AVAILABLE.value, index=True, nullable=False)
    duty_hours_accumulated: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    home_zone_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("zones.id"), nullable=False)

    home_zone: Mapped["Zone"] = relationship("Zone", back_populates="personnel")
    qualifications: Mapped[list["PersonnelQualification"]] = relationship("PersonnelQualification", back_populates="personnel")


class Qualification(BaseModel):
    """Skill and certification definitions (e.g. QUAL_NIGHT_OPS, QUAL_AVIONICS_LV3)."""

    __tablename__ = "qualifications"

    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    validity_days: Mapped[int] = mapped_column(Integer, default=365, nullable=False)


class PersonnelQualification(BaseModel):
    """Join entity for personnel qualifications and certification expiration dates."""

    __tablename__ = "personnel_qualifications"

    personnel_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("personnel.id"), nullable=False)
    qualification_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("qualifications.id"), nullable=False)
    acquired_at: Mapped[datetime] = mapped_column(default=lambda: get_clock().now(), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)

    personnel: Mapped["Personnel"] = relationship("Personnel", back_populates="qualifications")
    qualification: Mapped["Qualification"] = relationship("Qualification")


class ResourceInventory(BaseModel):
    """Base supplies and consumable inventory tracking per zone."""

    __tablename__ = "resource_inventory"

    item_code: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    zone_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("zones.id"), nullable=False)
    quantity_on_hand: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reorder_threshold: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
