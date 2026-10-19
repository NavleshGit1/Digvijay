from datetime import datetime, timezone
import pytest

from app.core.clock import FixedClock, SimulatedClock, SystemClock
from app.core.enums import ClockMode


def test_system_clock():
    clock = SystemClock()
    assert clock.mode() == ClockMode.SYSTEM
    now = clock.now()
    assert now.tzinfo is not None
    assert abs((clock.as_of() - now).total_seconds()) < 1.0


def test_fixed_clock():
    fixed_time = datetime(2026, 10, 19, 12, 0, 0, tzinfo=timezone.utc)
    clock = FixedClock(fixed_time)
    assert clock.mode() == ClockMode.FIXED
    assert clock.now() == fixed_time
    assert clock.as_of() == fixed_time

    # Update pinned time
    new_time = datetime(2026, 10, 20, 15, 30, 0, tzinfo=timezone.utc)
    clock.set_time(new_time)
    assert clock.now() == new_time


def test_simulated_clock():
    start_time = datetime(2026, 10, 19, 8, 0, 0, tzinfo=timezone.utc)
    clock = SimulatedClock(start_time, time_scale=1.0)
    assert clock.mode() == ClockMode.SIMULATED
    assert clock.now() == start_time

    # Advance clock by 3600 seconds (1 hour)
    advanced = clock.advance(3600)
    assert advanced == datetime(2026, 10, 19, 9, 0, 0, tzinfo=timezone.utc)
    assert clock.now() == advanced
