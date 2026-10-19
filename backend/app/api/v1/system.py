from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_clock, get_db, require_permission
from app.core.clock import Clock
from app.core.config import settings
from app.core.enums import ClockMode, UserRole
from app.core.health import health_registry
from app.models.identity import User
from app.schemas.clock import ClockState, ClockUpdateRequest
from app.services.audit import write_audit_entry
from app.services.clock import init_system_clock, update_system_clock

router = APIRouter(prefix="/system", tags=["System"])


@router.get("/clock", response_model=ClockState)
def get_system_clock(
    db: Session = Depends(get_db),
    clock: Clock = Depends(get_clock),
) -> ClockState:
    """Returns current operational clock state and as-of time."""
    init_system_clock(db)
    return ClockState(
        mode=clock.mode(),
        current_as_of=clock.now(),
        time_scale=1.0,
    )


@router.put("/clock", response_model=ClockState)
def update_clock(
    request: ClockUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(UserRole.ADMIN)),
) -> ClockState:
    """Updates, pins, or advances the virtual clock (Admin only, audited)."""
    updated_state = update_system_clock(
        db=db,
        mode=request.mode,
        target_time=request.target_time,
        advance_seconds=request.advance_seconds,
        time_scale=request.time_scale,
    )

    write_audit_entry(
        db=db,
        actor_id=current_user.id,
        role=UserRole.ADMIN.value,
        action="UPDATE_CLOCK",
        entity_type="system_clock_state",
        entity_id=str(updated_state.id),
        reason=f"Clock adjusted to mode={request.mode.value}, as_of={updated_state.current_as_of.isoformat()}",
        after_state={"mode": updated_state.mode, "current_as_of": updated_state.current_as_of.isoformat()},
    )
    db.commit()

    return ClockState(
        mode=ClockMode(updated_state.mode),
        current_as_of=updated_state.current_as_of,
        time_scale=updated_state.time_scale,
    )


@router.get("/health")
def get_health() -> dict[str, Any]:
    """Returns status of all modular monolith engines and circuit breakers."""
    return {
        "status": "healthy",
        "engines": health_registry.all_statuses(),
    }


@router.get("/environment")
def get_environment() -> dict[str, Any]:
    """Returns environment build, demo mode flag, and system metadata."""
    return {
        "environment": settings.ENVIRONMENT,
        "demo_mode": settings.DEMO_MODE,
        "debug": settings.DEBUG,
        "version": "1.0.0-synthetic-prototype",
        "dataset_version": "v1.0-synthetic-seed42",
    }


@router.get("/data-sources")
def get_data_sources(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    """Returns registered data connectors and live freshness SLA status."""
    from app.engines.data_fusion.freshness import evaluate_all_data_source_freshness
    return evaluate_all_data_source_freshness(db)

