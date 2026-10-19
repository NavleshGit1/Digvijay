from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_clock, get_db
from app.core.clock import Clock
from app.schemas.overview import OverviewKPIResponse
from app.services.kpi import KpiService

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
    kpi_service = KpiService(db)
    return kpi_service.calculate_overview_kpis(as_of=effective_as_of)

