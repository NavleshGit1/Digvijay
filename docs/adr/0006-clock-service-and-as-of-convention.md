# ADR 0006: System Clock Service and As-Of Injection Convention

- **Status:** Accepted
- **Date:** 2026-10-19
- **Deciders:** Platform, QA & Simulation Team (Stream A, E)

---

## Context and Problem Statement
Operational calculations (overdue maintenance, resource availability, task execution locking, frozen windows, alert threshold evaluations, and replanning) depend on the current time ("now"). Calling the operating system clock directly causes repeated test runs and scripted demonstrations to differ over time, breaking the core reproducibility principle.

## Considered Options
1. **Direct `datetime.now(timezone.utc)` calls:** Standard Python convention, but inherently non-reproducible across different days.
2. **Centralized Clock Service with Dependency Injection and Stored `as_of`:** Abstract `Clock` Protocol with three implementations (`SystemClock`, `FixedClock`, `SimulatedClock`), stored time state in PostgreSQL/Redis, and mandatory `as_of` timestamp parameters.

## Decision Outcome
Chosen option: **Centralized Clock Service** (Option 2).

### Implementation Rules
1. **Clock Protocol (`app.core.clock`):**
   ```python
   class Clock(Protocol):
       def now(self) -> datetime: ...
       def as_of(self) -> datetime: ...
   ```
   - `SystemClock`: Reads system UTC time (production/live default).
   - `FixedClock`: Returns a pinned UTC timestamp for deterministic demo scripts.
   - `SimulatedClock`: Supports time advancement (step/tick) for the SimPy digital twin and accelerated demo runs.
2. **Strict Ban on Direct Time Calls:** Direct invocations of `datetime.now()`, `datetime.utcnow()`, and `time.time()` are prohibited in business logic. An automated AST lint rule and CI check enforce this ban.
3. **Stored `as_of` on All Derived Artifacts:**
   - Every `dataset_version`, `plan_version`, `prediction`, `simulation_run`, and `report` must explicitly store the `as_of` timestamp used during its creation.
   - All KPI endpoints accept an optional `as_of` query parameter that defaults to `Clock.now()`.
4. **Shared State:** In demo mode, the clock state is persisted in `system_clock_state` and cached in Redis so that the FastAPI API server and all Celery workers agree on the exact same virtual time.
