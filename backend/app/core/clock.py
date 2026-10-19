from datetime import datetime, timezone
from typing import Protocol

from app.core.enums import ClockMode


class Clock(Protocol):
    """
    Clock Protocol for AirOps Nexus.
    Enforces ADR 0006: System Clock Service and As-Of Injection Convention.
    Direct calls to datetime.now() in business logic are banned.
    """

    def now(self) -> datetime:
        """Returns the current operational time."""
        ...

    def as_of(self) -> datetime:
        """Returns the as_of timestamp for snapshot queries."""
        ...

    def mode(self) -> ClockMode:
        """Returns the active clock mode."""
        ...


class SystemClock:
    """Standard system clock operating in real-world UTC time."""

    def now(self) -> datetime:
        return datetime.now(timezone.utc)

    def as_of(self) -> datetime:
        return self.now()

    def mode(self) -> ClockMode:
        return ClockMode.SYSTEM


class FixedClock:
    """Fixed clock pinned to a specific timestamp for deterministic demos."""

    def __init__(self, pinned_time: datetime) -> None:
        if pinned_time.tzinfo is None:
            pinned_time = pinned_time.replace(tzinfo=timezone.utc)
        self._pinned_time = pinned_time

    def set_time(self, new_time: datetime) -> None:
        if new_time.tzinfo is None:
            new_time = new_time.replace(tzinfo=timezone.utc)
        self._pinned_time = new_time

    def now(self) -> datetime:
        return self._pinned_time

    def as_of(self) -> datetime:
        return self._pinned_time

    def mode(self) -> ClockMode:
        return ClockMode.FIXED


class SimulatedClock:
    """Simulated clock supporting programmatic advancement for digital twin."""

    def __init__(self, start_time: datetime, time_scale: float = 1.0) -> None:
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
        self._current_time = start_time
        self._time_scale = time_scale

    def advance(self, seconds: float) -> datetime:
        from datetime import timedelta

        self._current_time += timedelta(seconds=seconds)
        return self._current_time

    def now(self) -> datetime:
        return self._current_time

    def as_of(self) -> datetime:
        return self._current_time

    def mode(self) -> ClockMode:
        return ClockMode.SIMULATED


# Global clock instance defaulted to SystemClock
_global_clock: Clock = SystemClock()


def get_clock() -> Clock:
    """Dependency provider returning the currently active clock."""
    return _global_clock


def set_global_clock(clock: Clock) -> None:
    """Updates the active clock implementation (Admin only)."""
    global _global_clock
    _global_clock = clock
