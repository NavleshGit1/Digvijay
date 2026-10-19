from datetime import datetime
from pydantic import BaseModel

from app.core.enums import ClockMode


class ClockState(BaseModel):
    mode: ClockMode
    current_as_of: datetime
    time_scale: float = 1.0


class ClockUpdateRequest(BaseModel):
    mode: ClockMode
    target_time: datetime | None = None
    advance_seconds: float | None = None
    time_scale: float | None = None
