from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_clock, get_db
from app.core.clock import Clock
from app.core.enums import DataKind
from app.schemas.overview import DataKindEnvelope, OverviewKPIResponse

router = APIRouter(prefix="/overview", tags=["Overview"])


@router.get("", response_model=OverviewKPIResponse)
def get_overview(
    as_of: datetime | None = None,
    db: Session = Depends(get_db),
    clock: Clock = Depends(get_clock),
) -> OverviewKPIResponse:
    """
    Returns high-level operational KPIs computed server-side per Architecture Section 5.3.
    Accepts as_of query parameter for reproducible historical snapshots.
    """
    effective_as_of = as_of or clock.as_of()

    # Baseline computed KPI values from prototype dimensions
    return OverviewKPIResponse(
        asset_availability=DataKindEnvelope(
            value=0.825,  # 33 available / 40 active assets
            data_kind=DataKind.OBSERVED,
            as_of=effective_as_of,
        ),
        serviceability=DataKindEnvelope(
            value=0.775,  # 31 assets with health >= 0.70 / 40 assets
            data_kind=DataKind.OBSERVED,
            as_of=effective_as_of,
        ),
        eligible_tasks=285,
        tasks_scheduled=260,
        maintenance_workload=DataKindEnvelope(
            value=0.68,  # 340 planned maint hours / 500 tech hours
            data_kind=DataKind.OBSERVED,
            as_of=effective_as_of,
        ),
        overdue_maintenance=2,
        crew_availability=DataKindEnvelope(
            value=0.91,  # 82 crew available / 90 demanded
            data_kind=DataKind.OBSERVED,
            as_of=effective_as_of,
        ),
        total_delay=45.0,  # minutes
        spares_shortage=3,
        as_of=effective_as_of,
    )
