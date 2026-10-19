import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_clock, require_permission
from app.core.clock import Clock
from app.core.enums import UserRole
from app.db.session import get_db
from app.models.identity import User
from app.models.provenance import Event
from app.schemas.events import EventCreate, EventOut
from app.services.audit import write_audit_entry

router = APIRouter(tags=["events"])


@router.get("/events", response_model=list[EventOut])
def list_events(
    event_type: str | None = Query(None, description="Filter by event type"),
    severity: str | None = Query(None, description="Filter by severity"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[Event]:
    """Retrieve operational event log and disruption stream."""
    stmt = select(Event)
    if event_type:
        stmt = stmt.where(Event.event_type == event_type)
    if severity:
        stmt = stmt.where(Event.severity == severity)

    stmt = stmt.order_by(Event.timestamp.desc()).limit(limit)
    return list(db.execute(stmt).scalars().all())


@router.post("/events", response_model=EventOut, status_code=status.HTTP_201_CREATED)
def inject_disruption_event(
    payload: EventCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission([UserRole.PLANNER, UserRole.ADMIN])),
    clock: Clock = Depends(get_clock),
) -> EventOut:
    """Inject a simulated disruption event (e.g. asset breakdown, maintenance delay) with full audit logging."""
    now = clock.now()
    idempotency_key = payload.idempotency_key or f"inject_{uuid.uuid4().hex[:12]}"

    event = Event(
        idempotency_key=idempotency_key,
        event_type=payload.event_type,
        source="manual_inject",
        affected_entity_type=payload.affected_entity_type,
        affected_entity_id=payload.affected_entity_id,
        severity=payload.severity,
        payload_json=payload.payload_json,
        timestamp=now,
    )
    db.add(event)
    db.flush()

    user_role = current_user.roles[0].name if current_user.roles else "planner"
    write_audit_entry(
        db=db,
        actor_id=current_user.id,
        role=user_role,
        action="INJECT_DISRUPTION_EVENT",
        entity_type="event",
        entity_id=str(event.id),
        reason=payload.reason,
        before_state=None,
        after_state={
            "event_type": payload.event_type,
            "affected_entity_type": payload.affected_entity_type,
            "affected_entity_id": payload.affected_entity_id,
            "severity": payload.severity,
            "idempotency_key": idempotency_key,
        },
    )
    db.commit()
    db.refresh(event)

    return EventOut(
        id=event.id,
        idempotency_key=event.idempotency_key,
        event_type=event.event_type,
        source=event.source,
        affected_entity_type=event.affected_entity_type,
        affected_entity_id=event.affected_entity_id,
        severity=event.severity,
        payload_json=event.payload_json,
        timestamp=event.timestamp,
    )
