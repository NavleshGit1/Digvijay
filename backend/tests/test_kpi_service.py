from datetime import datetime, timezone
import pytest
from app.db.session import SessionLocal
from app.engines.data_fusion.generator import seed_database
from app.services.kpi import KpiService


def test_kpi_service_accuracy():
    db = SessionLocal()
    try:
        fixed_dt = datetime(2026, 10, 20, 12, 0, 0, tzinfo=timezone.utc)
        # Seed deterministic dataset
        seed_database(db=db, seed=42, as_of=fixed_dt, reset=True)

        kpi_service = KpiService(db)
        kpis = kpi_service.calculate_overview_kpis(as_of=fixed_dt)

        # 1. Assets: 40 total, availability ratio should be close to ~0.95 (38/40)
        assert 0.80 <= kpis.asset_availability.value <= 1.0
        assert kpis.asset_availability.data_kind.value == "observed"

        # 2. Serviceability: ready assets / 40
        assert 0.70 <= kpis.serviceability.value <= 1.0

        # 3. Eligible tasks in 7-day horizon: should be non-zero and <= 300
        assert 200 <= kpis.eligible_tasks <= 300

        # 4. Spares shortage: exactly the 3 controlled shortage parts generated in Base Alpha
        assert kpis.spares_shortage == 3

        # 5. Total delay: sum of task execution delays
        assert kpis.total_delay > 0.0

        # 6. Crew availability: ratio between 0.70 and 1.0
        assert 0.70 <= kpis.crew_availability.value <= 1.0
    finally:
        db.close()
