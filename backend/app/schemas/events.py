import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class EventOut(BaseModel):
    id: uuid.UUID
    idempotency_key: str
    event_type: str
    source: str
    affected_entity_type: str
    affected_entity_id: str
    severity: str
    payload_json: dict
    timestamp: datetime

    model_config = {"from_attributes": True}


class EventCreate(BaseModel):
    event_type: str
    affected_entity_type: str
    affected_entity_id: str
    severity: str = "medium"
    payload_json: dict = Field(default_factory=dict)
    reason: str = Field(..., min_length=3, description="Mandatory reason for audit log")
    idempotency_key: str | None = None
