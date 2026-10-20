"""Alerts Management REST API (Phase 6, Tasks P6-11 & P6-12)."""
from datetime import datetime
from typing import Any
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.api.deps import get_clock, require_permission
from app.core.clock import Clock
from app.core.enums import UserRole
from app.db.session import get_db
from app.models.alerts import Alert, AlertRule
from app.models.identity import User
from app.services.alerts import (
    acknowledge_alert,
    evaluate_system_alerts,
    resolve_alert,
    seed_default_alert_rules,
)

router = APIRouter(prefix="/alerts", tags=["Alerts"])


class AlertOut(BaseModel):
    id: uuid.UUID
    rule_code: str
    title: str
    message: str
    severity: str
    status: str
    dedup_key: str
    entity_type: str
    entity_id: str
    payload_json: dict[str, Any]
    count: int
    first_seen: datetime
    last_seen: datetime
    acknowledged_at: datetime | None
    acknowledged_by: str | None
    resolved_at: datetime | None
    resolved_by: str | None

    class Config:
        from_attributes = True


class AlertSummary(BaseModel):
    total_active: int
    new_count: int
    acknowledged_count: int
    critical_count: int
    high_count: int
    medium_count: int


@router.get("", response_model=list[AlertOut])
def list_alerts(
    status_filter: str | None = Query(None, alias="status", description="Filter by status (new, acknowledged, resolved)"),
    severity: str | None = Query(None, description="Filter by severity (critical, high, medium, low)"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[Alert]:
    """Retrieves operational alerts stream with anti-flapping deduplication."""
    stmt = select(Alert)
    if status_filter:
        stmt = stmt.where(Alert.status == status_filter)
    else:
        # Default: show active (new and acknowledged) alerts
        stmt = stmt.where(Alert.status.in_(["new", "acknowledged"]))

    if severity:
        stmt = stmt.where(Alert.severity == severity)

    stmt = stmt.order_by(desc(Alert.last_seen)).limit(limit)
    return list(db.execute(stmt).scalars().all())


@router.get("/summary", response_model=AlertSummary)
def get_alert_summary(db: Session = Depends(get_db)) -> AlertSummary:
    """Returns aggregated severity and status counts of active operational alerts."""
    alerts = (
        db.execute(select(Alert).where(Alert.status.in_(["new", "acknowledged"])))
        .scalars()
        .all()
    )

    new_c = sum(1 for a in alerts if a.status == "new")
    ack_c = sum(1 for a in alerts if a.status == "acknowledged")
    crit_c = sum(1 for a in alerts if a.severity == "critical")
    high_c = sum(1 for a in alerts if a.severity == "high")
    med_c = sum(1 for a in alerts if a.severity == "medium")

    return AlertSummary(
        total_active=len(alerts),
        new_count=new_c,
        acknowledged_count=ack_c,
        critical_count=crit_c,
        high_count=high_c,
        medium_count=med_c,
    )


@router.post("/evaluate")
def trigger_alert_evaluation(
    db: Session = Depends(get_db),
    clock: Clock = Depends(get_clock),
    current_user: User = Depends(require_permission([UserRole.PLANNER, UserRole.ADMIN, UserRole.REVIEWER])),
) -> dict[str, Any]:
    """Manually triggers evaluation of all operational alert rules."""
    return evaluate_system_alerts(db, now=clock.now())


@router.post("/{alert_id}/acknowledge", response_model=AlertOut)
def acknowledge_alert_endpoint(
    alert_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission([UserRole.PLANNER, UserRole.REVIEWER, UserRole.ADMIN])),
) -> Alert:
    """Marks an active alert as acknowledged by the current operator."""
    try:
        return acknowledge_alert(db, alert_id, current_user.email)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/{alert_id}/resolve", response_model=AlertOut)
def resolve_alert_endpoint(
    alert_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission([UserRole.PLANNER, UserRole.REVIEWER, UserRole.ADMIN])),
) -> Alert:
    """Marks an active alert as resolved."""
    try:
        return resolve_alert(db, alert_id, current_user.email)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
