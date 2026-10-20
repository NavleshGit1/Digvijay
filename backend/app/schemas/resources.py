import uuid
from datetime import datetime
from pydantic import BaseModel, Field


# ==========================================
# Zones
# ==========================================

class ZoneOut(BaseModel):
    id: uuid.UUID
    name: str
    code: str
    capacity_limit: int
    coordinates_geojson: dict | None = None

    model_config = {"from_attributes": True}


# ==========================================
# Assets
# ==========================================

class AssetOut(BaseModel):
    id: uuid.UUID
    identifier: str
    asset_type: str
    model_name: str
    status: str
    health_score: float
    zone_id: uuid.UUID
    zone_code: str
    zone_name: str
    current_location: str | None = None
    flight_hours: float
    cycles: int
    has_active_maintenance: bool = False

    model_config = {"from_attributes": True, "protected_namespaces": ()}


class AssetDetailOut(AssetOut):
    recent_maintenance: list["MaintenanceRecordOut"] = []
    usage_summary: dict = Field(default_factory=dict)
    model_config = {"from_attributes": True, "protected_namespaces": ()}


class AssetUpdate(BaseModel):
    status: str | None = None
    current_location: str | None = None
    zone_id: uuid.UUID | None = None
    health_score: float | None = None
    reason: str = Field(..., min_length=3, description="Mandatory reason for audit log")


# ==========================================
# Personnel & Qualifications
# ==========================================

class QualificationOut(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    validity_days: int

    model_config = {"from_attributes": True}


class PersonnelQualificationOut(BaseModel):
    qualification_code: str
    qualification_name: str
    acquired_at: datetime
    expires_at: datetime
    is_expired: bool


class PersonnelOut(BaseModel):
    id: uuid.UUID
    name: str
    callsign: str | None = None
    role_type: str
    status: str
    duty_hours_accumulated: float
    home_zone_id: uuid.UUID
    home_zone_name: str
    qualifications: list[str] = []

    model_config = {"from_attributes": True}


class PersonnelDetailOut(PersonnelOut):
    qualification_details: list[PersonnelQualificationOut] = []


class PersonnelUpdate(BaseModel):
    status: str | None = None
    duty_hours_accumulated: float | None = None
    home_zone_id: uuid.UUID | None = None
    reason: str = Field(..., min_length=3, description="Mandatory reason for audit log")


# ==========================================
# Tasks & Dependencies
# ==========================================

class TaskRequirementOut(BaseModel):
    asset_type_required: str
    crew_headcount: int
    required_qualification_code: str | None = None

    model_config = {"from_attributes": True}


class TaskOut(BaseModel):
    id: uuid.UUID
    code: str
    category: str
    zone_id: uuid.UUID
    zone_name: str
    earliest_start: datetime
    latest_end: datetime
    duration_minutes: int
    priority: str
    weight: float
    status: str
    requirements: list[TaskRequirementOut] = []

    model_config = {"from_attributes": True}


class TaskDetailOut(TaskOut):
    predecessors: list[dict] = []
    successors: list[dict] = []


class TaskUpdate(BaseModel):
    status: str | None = None
    reason: str = Field(..., min_length=3, description="Mandatory reason for audit log")


# ==========================================
# Logistics & Spares Inventory
# ==========================================

class PartOut(BaseModel):
    id: uuid.UUID
    part_number: str
    name: str
    category: str
    unit_cost: float

    model_config = {"from_attributes": True}


class SparesInventoryOut(BaseModel):
    id: uuid.UUID
    part_id: uuid.UUID
    part_number: str
    part_name: str
    category: str
    zone_id: uuid.UUID
    zone_name: str
    on_hand: int
    reserved: int
    minimum_safety_level: int
    is_shortage: bool

    model_config = {"from_attributes": True}


class ResupplyOrderCreate(BaseModel):
    part_id: uuid.UUID
    zone_id: uuid.UUID
    quantity: int = Field(..., gt=0)
    reason: str = Field(..., min_length=3, description="Mandatory reason for audit log")


class ResupplyOrderOut(BaseModel):
    id: uuid.UUID
    part_id: uuid.UUID
    part_number: str
    part_name: str
    zone_id: uuid.UUID
    zone_name: str
    quantity: int
    ordered_at: datetime
    estimated_arrival: datetime
    status: str

    model_config = {"from_attributes": True}


# ==========================================
# Maintenance
# ==========================================

class MaintenanceRecordOut(BaseModel):
    id: uuid.UUID
    asset_id: uuid.UUID
    asset_identifier: str
    category: str
    start_time: datetime
    end_time: datetime
    predicted_completion: datetime | None = None
    is_unplanned: bool
    status: str
    is_overdue: bool = False

    model_config = {"from_attributes": True}


class MaintenanceRecordCreate(BaseModel):
    asset_id: uuid.UUID
    category: str
    start_time: datetime
    end_time: datetime
    is_unplanned: bool = False
    reason: str = Field(..., min_length=3, description="Mandatory reason for audit log")


class MaintenanceValidationRequest(BaseModel):
    asset_id: uuid.UUID
    start_time: datetime
    end_time: datetime
    task_id: uuid.UUID | None = None


class MaintenanceValidationResponse(BaseModel):
    is_compatible: bool
    conflict_details: str | None = None
    conflicting_record_id: uuid.UUID | None = None


class MaintenanceRecordUpdate(BaseModel):
    category: str | None = None
    status: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    predicted_completion: datetime | None = None
    is_unplanned: bool | None = None
    reason: str = Field(..., min_length=3, description="Mandatory reason for audit log")


class MaintenanceDelaySimulateRequest(BaseModel):
    delay_minutes: float = Field(default=120.0, ge=1.0, le=1440.0, description="Maintenance window extension in minutes")
    reason: str = Field(default="Unscheduled avionics repair delay", min_length=3)


# Fix forward reference
AssetDetailOut.model_rebuild()
