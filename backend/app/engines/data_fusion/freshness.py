"""
Data Source Freshness Evaluator (Phase 2 Task P2-5 & Architecture Section 3.2).
Evaluates ingestion heartbeat SLA compliance against the virtual clock.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import get_clock
from app.models.provenance import DataSource, DataSourceFreshness


def evaluate_all_data_source_freshness(db: Session) -> list[dict]:
    """
    Evaluates freshness for all registered data sources against the current virtual clock.
    Updates or creates DataSourceFreshness records.
    """
    clock = get_clock()
    now = clock.now()
    stmt = select(DataSource).where(DataSource.is_active == True)
    sources = db.execute(stmt).scalars().all()

    results = []
    for s in sources:
        # Lookup freshness row
        f_stmt = select(DataSourceFreshness).where(DataSourceFreshness.source_id == s.id)
        freshness = db.execute(f_stmt).scalars().first()

        if freshness:
            staleness = (now - freshness.last_successful_sync).total_seconds()
            staleness = max(0.0, staleness)
            # Threshold is 1.5x expected interval
            threshold = s.expected_interval_seconds * 1.5
            is_stale = staleness > threshold

            freshness.staleness_seconds = staleness
            freshness.is_stale = is_stale
            freshness.updated_at = now
        else:
            staleness = 0.0
            is_stale = False

        results.append({
            "source_id": str(s.id),
            "source_name": s.name,
            "adapter_type": s.adapter_type,
            "expected_interval_seconds": s.expected_interval_seconds,
            "staleness_seconds": staleness,
            "is_stale": is_stale,
            "status": "stale" if is_stale else "fresh",
        })

    db.commit()
    return results
