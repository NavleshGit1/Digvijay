import uuid
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import get_clock
from app.models.operations import MaintenanceRecord
from app.models.resources import Asset


def validate_maintenance_overlap(
    db: Session,
    asset_id: uuid.UUID,
    start_time: datetime,
    end_time: datetime,
    exclude_record_id: uuid.UUID | None = None,
) -> tuple[bool, str | None, MaintenanceRecord | None]:
    """
    Hard Maintenance Window Validation Rule (Phase 3 Task P3-2).
    Rejects any task assignment or overlapping maintenance window if the asset
    is already committed to scheduled or in-progress maintenance.

    Rule condition:
    start_time < record.end_time AND end_time > record.start_time
    """
    if start_time >= end_time:
        return False, "Validation error: start_time must precede end_time.", None

    asset = db.get(Asset, asset_id)
    if not asset:
        return False, f"Asset with ID '{asset_id}' not found.", None

    stmt = (
        select(MaintenanceRecord)
        .where(
            MaintenanceRecord.asset_id == asset_id,
            MaintenanceRecord.status.in_(["scheduled", "in_progress"]),
            MaintenanceRecord.start_time < end_time,
            MaintenanceRecord.end_time > start_time,
        )
        .order_by(MaintenanceRecord.start_time.asc())
    )

    if exclude_record_id:
        stmt = stmt.where(MaintenanceRecord.id != exclude_record_id)

    conflicting_record = db.execute(stmt).scalars().first()

    if conflicting_record:
        fmt_start = conflicting_record.start_time.strftime("%Y-%m-%d %H:%M UTC")
        fmt_end = conflicting_record.end_time.strftime("%Y-%m-%d %H:%M UTC")
        msg = (
            f"Hard Maintenance Window Conflict: Asset '{asset.identifier}' is committed to "
            f"maintenance '{conflicting_record.category}' from {fmt_start} to {fmt_end} "
            f"(Record ID: {conflicting_record.id}). Incompatible with requested window."
        )
        return False, msg, conflicting_record

    return True, None, None
