import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: uuid.UUID
    actor_id: uuid.UUID | None = None
    role: str
    action: str
    entity_type: str
    entity_id: str | None = None
    before_state: dict[str, Any] | None = None
    after_state: dict[str, Any] | None = None
    plan_version_id: uuid.UUID | None = None
    reason: str
    request_id: str | None = None
    timestamp: datetime
    previous_hash: str
    record_hash: str

    model_config = {"from_attributes": True}
