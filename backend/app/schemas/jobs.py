import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel

from app.core.enums import JobState, SolverStatus


class JobCreateRequest(BaseModel):
    job_type: str = "dummy_job"
    duration_seconds: int = 5
    parameters: dict[str, Any] = {}


class JobResponse(BaseModel):
    id: uuid.UUID
    job_type: str
    state: JobState
    progress_percent: float
    message: str | None = None
    result_id: str | None = None
    solver_status: SolverStatus | None = None
    error_details: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
