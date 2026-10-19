import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import FixedClock, SimulatedClock, SystemClock, get_clock, set_global_clock
from app.core.enums import ClockMode
from app.core.locks import redis_client
from app.models.clock import SystemClockState


def init_system_clock(db: Session) -> SystemClockState:
    """Initializes or reads system clock state from database and synchronizes global clock."""
    stmt = select(SystemClockState).limit(1)
    clock_state = db.execute(stmt).scalars().first()

    if not clock_state:
        clock_state = SystemClockState(
            id=uuid.uuid4(),
            mode=ClockMode.SYSTEM.value,
            current_as_of=get_clock().now(),
            time_scale=1.0,
        )
        db.add(clock_state)
        db.commit()
        db.refresh(clock_state)

    apply_clock_state(clock_state)
    return clock_state


def apply_clock_state(clock_state: SystemClockState) -> None:
    """Applies the database clock state to the in-memory global Clock."""
    if clock_state.mode == ClockMode.FIXED.value:
        set_global_clock(FixedClock(clock_state.current_as_of))
    elif clock_state.mode == ClockMode.SIMULATED.value:
        set_global_clock(SimulatedClock(clock_state.current_as_of, clock_state.time_scale))
    else:
        set_global_clock(SystemClock())

    # Cache current as_of in Redis for distributed worker synchronization
    try:
        redis_client.set("system:clock:mode", clock_state.mode)
        redis_client.set("system:clock:as_of", clock_state.current_as_of.isoformat())
    except Exception:
        pass


def update_system_clock(
    db: Session,
    mode: ClockMode,
    target_time: datetime | None = None,
    advance_seconds: float | None = None,
    time_scale: float | None = None,
) -> SystemClockState:
    """Updates the virtual clock mode and timestamp in database and Redis."""
    stmt = select(SystemClockState).limit(1)
    clock_state = db.execute(stmt).scalars().first()

    if not clock_state:
        clock_state = init_system_clock(db)

    clock_state.mode = mode.value

    if target_time:
        if target_time.tzinfo is None:
            target_time = target_time.replace(tzinfo=timezone.utc)
        clock_state.current_as_of = target_time
    elif advance_seconds:
        from datetime import timedelta
        clock_state.current_as_of += timedelta(seconds=advance_seconds)

    if time_scale is not None:
        clock_state.time_scale = time_scale

    db.commit()
    db.refresh(clock_state)
    apply_clock_state(clock_state)
    return clock_state
