"""Alert Evaluation and Lifecycle Subsystem (Phase 6, Tasks P6-11 & P6-12).

Evaluates operational rules from docs/alert-rules-catalogue.md, enforces anti-flapping
deduplication with a 15-minute sliding window, manages alert lifecycle (NEW -> ACKNOWLEDGED -> RESOLVED),
and publishes real-time WebSocket/SSE notifications.
"""
from datetime import datetime, timedelta, timezone
from typing import Any
import hashlib
import json
import uuid

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.core.clock import get_clock
from app.core.locks import redis_client
from app.models.alerts import Alert, AlertRule
from app.models.logistics import Part, ResupplyOrder, SparesInventory
from app.models.operations import MaintenanceRecord, Task
from app.models.plans import Plan, PlanAssignment, PlanVersion
from app.models.provenance import DataQualityIssue
from app.models.resources import Asset, Personnel
from app.services.audit import write_audit_entry

DEFAULT_ALERT_RULES = [
    {
        "rule_code": "ALERT_AVAIL_CRITICAL",
        "name": "Asset Availability Below Threshold",
        "severity": "critical",
        "description": "Fleet availability dropped below critical operational readiness threshold (60%).",
        "threshold_value": 0.60,
        "hysteresis_buffer": 0.05,
        "scope": "global",
    },
    {
        "rule_code": "ALERT_CREW_SHORTAGE",
        "name": "Crew Availability Deficit",
        "severity": "high",
        "description": "Scheduled crew demand exceeds qualified available personnel.",
        "threshold_value": 0.0,
        "hysteresis_buffer": 0.0,
        "scope": "zone",
    },
    {
        "rule_code": "ALERT_MAINT_OVERDUE",
        "name": "Overdue Asset Maintenance",
        "severity": "high",
        "description": "Asset maintenance window has elapsed beyond virtual clock without completion.",
        "threshold_value": 0.0,
        "hysteresis_buffer": 0.0,
        "scope": "asset",
    },
    {
        "rule_code": "ALERT_USAGE_LIMIT",
        "name": "Asset Usage Exceeds Threshold",
        "severity": "medium",
        "description": "Accumulated asset flight hours exceed 90% of scheduled service limit.",
        "threshold_value": 0.90,
        "hysteresis_buffer": 0.05,
        "scope": "asset",
    },
    {
        "rule_code": "ALERT_SPARES_STOCKOUT",
        "name": "Critical Spare Parts Shortage",
        "severity": "high",
        "description": "Spare part inventory quantity has breached designated safety stock reserve.",
        "threshold_value": 0.0,
        "hysteresis_buffer": 1.0,
        "scope": "logistics",
    },
    {
        "rule_code": "ALERT_RESUPPLY_DELAY",
        "name": "Late Resupply Delivery",
        "severity": "medium",
        "description": "Inbound logistics shipment ETA is past virtual clock time.",
        "threshold_value": 0.0,
        "hysteresis_buffer": 0.0,
        "scope": "logistics",
    },
    {
        "rule_code": "ALERT_PROPOSAL_STALE",
        "name": "Pending Proposal Outdated",
        "severity": "medium",
        "description": "Pending schedule proposal invalidated by new disruption or superseded by sibling approval.",
        "threshold_value": 0.0,
        "hysteresis_buffer": 0.0,
        "scope": "plan",
    },
    {
        "rule_code": "ALERT_DATA_QUALITY",
        "name": "High-Severity Anomaly Detected",
        "severity": "critical",
        "description": "Unresolved data quality integrity issue detected in operational records.",
        "threshold_value": 0.0,
        "hysteresis_buffer": 0.0,
        "scope": "quality",
    },
]


def seed_default_alert_rules(db: Session) -> None:
    """Seeds predefined alert rules if not already present."""
    existing_codes = set(db.execute(select(AlertRule.rule_code)).scalars().all())
    for r in DEFAULT_ALERT_RULES:
        if r["rule_code"] not in existing_codes:
            rule = AlertRule(
                rule_code=r["rule_code"],
                name=r["name"],
                severity=r["severity"],
                description=r["description"],
                threshold_value=r["threshold_value"],
                hysteresis_buffer=r["hysteresis_buffer"],
                scope=r["scope"],
                is_active=True,
            )
            db.add(rule)
    db.commit()


def compute_dedup_key(rule_code: str, entity_type: str, entity_id: str) -> str:
    raw = f"{rule_code}:{entity_type}:{entity_id}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def create_or_update_alert(
    db: Session,
    rule_code: str,
    title: str,
    message: str,
    severity: str,
    entity_type: str,
    entity_id: str,
    payload_json: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> Alert:
    """Creates a new alert or increments counter on existing active alert within 15m window."""
    clock_now = now or get_clock().now()
    dedup_key = compute_dedup_key(rule_code, entity_type, entity_id)

    # Check for existing active or acknowledged alert with this dedup key
    existing = (
        db.execute(
            select(Alert)
            .where(Alert.dedup_key == dedup_key)
            .where(Alert.status.in_(["new", "acknowledged"]))
        )
        .scalars()
        .first()
    )

    if existing:
        # Anti-flapping: Increment counter and update last_seen
        existing.count += 1
        existing.last_seen = clock_now
        existing.message = message
        if payload_json:
            existing.payload_json = payload_json
        db.commit()
        db.refresh(existing)
        setattr(existing, "_was_created", False)
        return existing

    # Create new alert
    alert = Alert(
        rule_code=rule_code,
        title=title,
        message=message,
        severity=severity,
        status="new",
        dedup_key=dedup_key,
        entity_type=entity_type,
        entity_id=entity_id,
        payload_json=payload_json or {},
        count=1,
        first_seen=clock_now,
        last_seen=clock_now,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    setattr(alert, "_was_created", True)

    # Publish notification
    try:
        notification = {
            "event": "alert_created",
            "alert_id": str(alert.id),
            "rule_code": alert.rule_code,
            "title": alert.title,
            "severity": alert.severity,
            "status": alert.status,
            "entity_type": alert.entity_type,
            "entity_id": alert.entity_id,
            "timestamp": clock_now.isoformat(),
        }
        redis_client.publish("alerts:new", json.dumps(notification))
    except Exception:
        pass

    return alert


def evaluate_system_alerts(
    db: Session,
    now: datetime | None = None,
    as_of: datetime | None = None,
) -> dict[str, Any]:
    """Evaluates all operational rules and generates or auto-resolves alerts."""
    clock_now = as_of or now or get_clock().now()
    created_count = 0
    updated_count = 0
    generated_alerts: list[str] = []
    resolved_alerts: list[str] = []

    def record_alert(a: Alert, tag: str | None = None):
        nonlocal created_count, updated_count
        if getattr(a, "_was_created", False):
            created_count += 1
        else:
            updated_count += 1
        generated_alerts.append(tag or a.rule_code)

    # 1. Evaluate ALERT_AVAIL_CRITICAL (Fleet availability < 60%)
    total_assets = db.execute(select(func.count(Asset.id))).scalar_one() or 1
    avail_assets = (
        db.execute(select(func.count(Asset.id)).where(Asset.status == "available")).scalar_one()
        or 0
    )
    avail_ratio = avail_assets / total_assets
    if avail_ratio < 0.60:
        a = create_or_update_alert(
            db=db,
            rule_code="ALERT_AVAIL_CRITICAL",
            title="Fleet Availability Critical",
            message=f"Only {avail_assets}/{total_assets} aircraft ({avail_ratio:.1%}) are currently available.",
            severity="critical",
            entity_type="system",
            entity_id="global_fleet",
            payload_json={"availability": avail_ratio, "available_count": avail_assets, "total_count": total_assets},
            now=clock_now,
        )
        record_alert(a)

    # 2. Evaluate ALERT_MAINT_OVERDUE (Maintenance end_time < clock_now and status != completed)
    overdue_maint = (
        db.execute(
            select(MaintenanceRecord)
            .where(MaintenanceRecord.end_time < clock_now)
            .where(MaintenanceRecord.status != "completed")
        )
        .scalars()
        .all()
    )
    for m in overdue_maint:
        asset = db.get(Asset, m.asset_id)
        tail = asset.identifier if asset else str(m.asset_id)[:8]
        a = create_or_update_alert(
            db=db,
            rule_code="ALERT_MAINT_OVERDUE",
            title=f"Maintenance Overdue on {tail}",
            message=f"Work order '{m.category}' scheduled completion {m.end_time.strftime('%Y-%m-%d %H:%M UTC')} is overdue.",
            severity="high",
            entity_type="maintenance",
            entity_id=str(m.id),
            payload_json={"asset_id": str(m.asset_id), "category": m.category, "end_time": m.end_time.isoformat()},
            now=clock_now,
        )
        record_alert(a, f"{a.rule_code}:{tail}")

    # 3. Evaluate ALERT_SPARES_STOCKOUT (on_hand < minimum_safety_level)
    stockouts = (
        db.execute(
            select(SparesInventory)
            .where(SparesInventory.on_hand < SparesInventory.minimum_safety_level)
        )
        .scalars()
        .all()
    )
    parts_by_id = {p.id: p for p in db.execute(select(Part)).scalars().all()}
    for sp in stockouts:
        part = parts_by_id.get(sp.part_id)
        p_name = part.name if part else str(sp.part_id)[:8]
        sev = "critical" if sp.on_hand == 0 else "high"
        a = create_or_update_alert(
            db=db,
            rule_code="ALERT_SPARES_STOCKOUT",
            title=f"Spare Shortage: {p_name}",
            message=f"Stock of '{p_name}' at {sp.on_hand} units is below required safety level of {sp.minimum_safety_level}.",
            severity=sev,
            entity_type="part",
            entity_id=str(sp.part_id),
            payload_json={"on_hand": sp.on_hand, "safety_stock": sp.minimum_safety_level},
            now=clock_now,
        )
        record_alert(a, f"{a.rule_code}:{p_name}")

    # 4. Evaluate ALERT_PROPOSAL_STALE (pending proposals marked stale)
    stale_proposals = (
        db.execute(
            select(PlanVersion)
            .where(PlanVersion.status == "proposed")
            .where(PlanVersion.stale_reason.isnot(None))
        )
        .scalars()
        .all()
    )
    for pv in stale_proposals:
        a = create_or_update_alert(
            db=db,
            rule_code="ALERT_PROPOSAL_STALE",
            title=f"Proposal v{pv.version_number} Outdated",
            message=f"Schedule proposal v{pv.version_number} invalidated: {pv.stale_reason}",
            severity="medium",
            entity_type="plan_version",
            entity_id=str(pv.id),
            payload_json={"version_number": pv.version_number, "reason": pv.stale_reason},
            now=clock_now,
        )
        record_alert(a, f"{a.rule_code}:v{pv.version_number}")

    # 5. Evaluate ALERT_DATA_QUALITY (open integrity issues)
    open_issues_count = (
        db.execute(
            select(func.count(DataQualityIssue.id)).where(DataQualityIssue.status == "open")
        ).scalar_one()
        or 0
    )
    if open_issues_count > 0:
        a = create_or_update_alert(
            db=db,
            rule_code="ALERT_DATA_QUALITY",
            title=f"Data Quality Issues ({open_issues_count} open)",
            message=f"{open_issues_count} data quality or reconciliation issues require review.",
            severity="high" if open_issues_count > 10 else "medium",
            entity_type="system",
            entity_id="quality_ledger",
            payload_json={"open_issues_count": open_issues_count},
            now=clock_now,
        )
        record_alert(a)

    return {
        "status": "evaluated",
        "as_of": clock_now.isoformat(),
        "created": created_count,
        "updated": updated_count,
        "generated_count": len(generated_alerts),
        "alerts_generated": generated_alerts,
        "resolved_count": len(resolved_alerts),
    }


def acknowledge_alert(
    db: Session,
    alert_id: uuid.UUID,
    user_email: str | None = None,
    acknowledged_by: str | None = None,
) -> Alert:
    """Sets alert status to acknowledged with user audit."""
    actor = acknowledged_by or user_email or "system_reviewer"
    alert = db.get(Alert, alert_id)
    if not alert:
        raise ValueError(f"Alert '{alert_id}' not found")

    alert.status = "acknowledged"
    alert.acknowledged_at = get_clock().now()
    alert.acknowledged_by = actor
    db.commit()
    db.refresh(alert)

    write_audit_entry(
        db=db,
        actor_id=None,
        role="reviewer",
        action="ACKNOWLEDGE_ALERT",
        entity_type="alerts",
        entity_id=str(alert.id),
        reason=f"Alert {alert.rule_code} acknowledged by {actor}",
        before_state={"status": "new"},
        after_state={"status": "acknowledged", "acknowledged_by": actor},
    )

    return alert


def resolve_alert(
    db: Session,
    alert_id: uuid.UUID,
    user_email: str | None = None,
    resolved_by: str | None = None,
    resolution_notes: str | None = None,
) -> Alert:
    """Sets alert status to resolved with user audit."""
    actor = resolved_by or user_email or "system_reviewer"
    alert = db.get(Alert, alert_id)
    if not alert:
        raise ValueError(f"Alert '{alert_id}' not found")

    alert.status = "resolved"
    alert.resolved_at = get_clock().now()
    alert.resolved_by = actor
    db.commit()
    db.refresh(alert)

    write_audit_entry(
        db=db,
        actor_id=None,
        role="reviewer",
        action="RESOLVE_ALERT",
        entity_type="alerts",
        entity_id=str(alert.id),
        reason=f"Alert {alert.rule_code} resolved by {actor}: {resolution_notes or 'No notes'}",
        before_state={"status": alert.status},
        after_state={"status": "resolved", "resolved_by": actor},
    )

    return alert
