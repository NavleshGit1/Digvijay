import hashlib
import json
import uuid
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import get_clock
from app.models.audit import AuditLog


def compute_audit_hash(
    previous_hash: str,
    actor_id: str | None,
    action: str,
    entity_type: str,
    entity_id: str | None,
    timestamp_str: str,
    reason: str,
    before_state: dict[str, Any] | None,
    after_state: dict[str, Any] | None,
) -> str:
    """Computes a SHA-256 hash chaining back to the previous record hash."""
    payload = {
        "previous_hash": previous_hash,
        "actor_id": str(actor_id) if actor_id else None,
        "action": action,
        "entity_type": entity_type,
        "entity_id": str(entity_id) if entity_id else None,
        "timestamp": timestamp_str,
        "reason": reason,
        "before_state": before_state,
        "after_state": after_state,
    }
    serialized = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def write_audit_entry(
    db: Session,
    actor_id: uuid.UUID | None,
    role: str,
    action: str,
    entity_type: str,
    entity_id: str | None,
    reason: str,
    before_state: dict[str, Any] | None = None,
    after_state: dict[str, Any] | None = None,
    plan_version_id: uuid.UUID | None = None,
    request_id: str | None = None,
) -> AuditLog:
    """Writes an append-only audit log row with verifiable SHA-256 hash chaining."""
    clock = get_clock()
    now = clock.now()

    # Query last audit entry to get previous_hash
    stmt = select(AuditLog.record_hash).order_by(AuditLog.timestamp.desc()).limit(1)
    last_hash = db.execute(stmt).scalar()
    previous_hash = last_hash if last_hash else "0" * 64

    record_hash = compute_audit_hash(
        previous_hash=previous_hash,
        actor_id=str(actor_id) if actor_id else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        timestamp_str=now.isoformat(),
        reason=reason,
        before_state=before_state,
        after_state=after_state,
    )

    audit_entry = AuditLog(
        id=uuid.uuid4(),
        actor_id=actor_id,
        role=role,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before_state=before_state,
        after_state=after_state,
        plan_version_id=plan_version_id,
        reason=reason,
        request_id=request_id,
        timestamp=now,
        previous_hash=previous_hash,
        record_hash=record_hash,
    )
    db.add(audit_entry)
    db.flush()
    return audit_entry
