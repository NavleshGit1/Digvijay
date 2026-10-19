from datetime import datetime
from typing import Any
from pydantic import BaseModel

from app.core.enums import DataKind


class DataKindEnvelope(BaseModel):
    value: Any
    data_kind: DataKind
    as_of: datetime
    model_version: str | None = None
    confidence_interval: list[float] | None = None

    model_config = {"protected_namespaces": ()}


class OverviewKPIResponse(BaseModel):
    asset_availability: DataKindEnvelope
    serviceability: DataKindEnvelope
    eligible_tasks: int
    tasks_scheduled: int
    maintenance_workload: DataKindEnvelope
    overdue_maintenance: int
    crew_availability: DataKindEnvelope
    total_delay: float
    spares_shortage: int
    as_of: datetime
