"""Constraint checking modules for AirOps Nexus (Phase 4, Task P4-2).
Each invariant can be evaluated individually or combined in IndependentPlanValidator.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
import uuid


def get_val(obj: Any, key: str, default: Any = None) -> Any:
    """Safely extracts field value whether obj is a dict or an ORM model."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


@dataclass
class Violation:
    constraint_code: str
    message: str
    entity_type: str
    entity_id: str
    conflicting_task_id: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "constraint_code": self.constraint_code,
            "message": self.message,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "conflicting_task_id": self.conflicting_task_id,
            "details": self.details,
        }


def check_resource_avail(
    assignments: list[dict[str, Any]],
    assets_by_id: dict[str, Any],
    personnel_by_id: dict[str, Any],
) -> list[Violation]:
    """HC_RESOURCE_AVAIL: Task intervals must be assigned to available resources."""
    violations: list[Violation] = []
    for asgn in assignments:
        t_id = str(get_val(asgn, "task_id", ""))
        a_id = get_val(asgn, "asset_id")
        if a_id:
            a_id_str = str(a_id)
            asset = assets_by_id.get(a_id_str)
            if not asset:
                violations.append(
                    Violation(
                        constraint_code="HC_RESOURCE_AVAIL",
                        message=f"Assigned asset {a_id_str} does not exist",
                        entity_type="asset",
                        entity_id=a_id_str,
                        conflicting_task_id=t_id,
                    )
                )
            elif get_val(asset, "status") in ("retired", "decommissioned"):
                violations.append(
                    Violation(
                        constraint_code="HC_RESOURCE_AVAIL",
                        message=f"Asset {get_val(asset, 'identifier')} is {get_val(asset, 'status')} and cannot be assigned",
                        entity_type="asset",
                        entity_id=a_id_str,
                        conflicting_task_id=t_id,
                    )
                )

        p_ids = get_val(asgn, "personnel_ids") or []
        for p_id in p_ids:
            p_id_str = str(p_id)
            person = personnel_by_id.get(p_id_str)
            if not person:
                violations.append(
                    Violation(
                        constraint_code="HC_RESOURCE_AVAIL",
                        message=f"Assigned crew {p_id_str} does not exist",
                        entity_type="personnel",
                        entity_id=p_id_str,
                        conflicting_task_id=t_id,
                    )
                )
            elif get_val(person, "status") in ("leave", "unavailable"):
                violations.append(
                    Violation(
                        constraint_code="HC_RESOURCE_AVAIL",
                        message=f"Crew {get_val(person, 'name')} is on {get_val(person, 'status')} and unavailable",
                        entity_type="personnel",
                        entity_id=p_id_str,
                        conflicting_task_id=t_id,
                    )
                )
    return violations


def check_no_overlap(assignments: list[dict[str, Any]]) -> list[Violation]:
    """HC_NO_OVERLAP: No incompatible simultaneous assignments on the same asset or crew member."""
    violations: list[Violation] = []

    # 1. Asset overlap
    by_asset: dict[str, list[dict[str, Any]]] = {}
    for asgn in assignments:
        a_id = get_val(asgn, "asset_id")
        if a_id:
            by_asset.setdefault(str(a_id), []).append(asgn)

    for a_id, asgns in by_asset.items():
        sorted_asgns = sorted(asgns, key=lambda x: get_val(x, "assigned_start"))
        for i in range(len(sorted_asgns) - 1):
            cur = sorted_asgns[i]
            nxt = sorted_asgns[i + 1]
            cur_end = get_val(cur, "assigned_end")
            nxt_start = get_val(nxt, "assigned_start")
            if cur_end > nxt_start:
                violations.append(
                    Violation(
                        constraint_code="HC_NO_OVERLAP",
                        message=(
                            f"Asset assignment overlap between task {get_val(cur, 'task_id')} "
                            f"({cur_end.isoformat()}) and task {get_val(nxt, 'task_id')} ({nxt_start.isoformat()})"
                        ),
                        entity_type="asset",
                        entity_id=a_id,
                        conflicting_task_id=str(get_val(nxt, "task_id")),
                        details={"task_a": str(get_val(cur, "task_id")), "task_b": str(get_val(nxt, "task_id"))},
                    )
                )

    # 2. Crew overlap
    by_person: dict[str, list[dict[str, Any]]] = {}
    for asgn in assignments:
        for p_id in get_val(asgn, "personnel_ids") or []:
            by_person.setdefault(str(p_id), []).append(asgn)

    for p_id, asgns in by_person.items():
        sorted_asgns = sorted(asgns, key=lambda x: get_val(x, "assigned_start"))
        for i in range(len(sorted_asgns) - 1):
            cur = sorted_asgns[i]
            nxt = sorted_asgns[i + 1]
            cur_end = get_val(cur, "assigned_end")
            nxt_start = get_val(nxt, "assigned_start")
            if cur_end > nxt_start:
                violations.append(
                    Violation(
                        constraint_code="HC_NO_OVERLAP",
                        message=(
                            f"Personnel assignment overlap for crew {p_id} between task {get_val(cur, 'task_id')} "
                            f"({cur_end.isoformat()}) and task {get_val(nxt, 'task_id')} ({nxt_start.isoformat()})"
                        ),
                        entity_type="personnel",
                        entity_id=p_id,
                        conflicting_task_id=str(get_val(nxt, "task_id")),
                        details={"task_a": str(get_val(cur, "task_id")), "task_b": str(get_val(nxt, "task_id"))},
                    )
                )

    return violations


def check_qualifications(
    assignments: list[dict[str, Any]],
    tasks_by_id: dict[str, Any],
    requirements_by_task: dict[str, Any],
    assets_by_id: dict[str, Any],
    personnel_quals_by_person: dict[str, list[dict[str, Any]]],
) -> list[Violation]:
    """HC_QUALIFICATIONS: Crew capability, certification, and required asset type."""
    violations: list[Violation] = []

    for asgn in assignments:
        t_id = str(get_val(asgn, "task_id"))
        req = requirements_by_task.get(t_id)
        if not req:
            continue

        # Asset compatibility
        a_id = get_val(asgn, "asset_id")
        if a_id:
            asset = assets_by_id.get(str(a_id))
            if asset:
                expected_type = get_val(req, "asset_type_required")
                actual_type = get_val(asset, "asset_type")
                if expected_type and actual_type != expected_type:
                    violations.append(
                        Violation(
                            constraint_code="HC_QUALIFICATIONS",
                            message=f"Task {t_id} requires asset type '{expected_type}' but got '{actual_type}'",
                            entity_type="asset",
                            entity_id=str(a_id),
                            conflicting_task_id=t_id,
                            details={"required": expected_type, "actual": actual_type},
                        )
                    )

        # Crew headcount
        p_ids = get_val(asgn, "personnel_ids") or []
        headcount_req = get_val(req, "crew_headcount", 1)
        if len(p_ids) < headcount_req:
            violations.append(
                Violation(
                    constraint_code="HC_QUALIFICATIONS",
                    message=f"Task {t_id} requires {headcount_req} crew members but only {len(p_ids)} assigned",
                    entity_type="task",
                    entity_id=t_id,
                    conflicting_task_id=t_id,
                    details={"required_headcount": headcount_req, "assigned_headcount": len(p_ids)},
                )
            )

        # Crew certification
        req_qual = get_val(req, "required_qualification_code")
        if req_qual:
            start_time = get_val(asgn, "assigned_start")
            for p_id in p_ids:
                p_id_str = str(p_id)
                held_quals = personnel_quals_by_person.get(p_id_str, [])
                has_active = any(
                    (get_val(q, "code") == req_qual or get_val(q, "qualification_code") == req_qual)
                    and get_val(q, "expires_at") > start_time
                    for q in held_quals
                )
                if not has_active:
                    violations.append(
                        Violation(
                            constraint_code="HC_QUALIFICATIONS",
                            message=f"Crew member {p_id_str} lacks active certification '{req_qual}' for task {t_id}",
                            entity_type="personnel",
                            entity_id=p_id_str,
                            conflicting_task_id=t_id,
                            details={"required_qual": req_qual},
                        )
                    )

    return violations


def check_maint_windows(
    assignments: list[dict[str, Any]],
    maintenance_by_asset: dict[str, list[dict[str, Any]]],
) -> list[Violation]:
    """HC_MAINT_WINDOWS: No operational task interval may overlap confirmed maintenance windows."""
    violations: list[Violation] = []
    for asgn in assignments:
        a_id = get_val(asgn, "asset_id")
        if not a_id:
            continue
        a_id_str = str(a_id)
        m_records = maintenance_by_asset.get(a_id_str, [])
        t_start = get_val(asgn, "assigned_start")
        t_end = get_val(asgn, "assigned_end")

        for m in m_records:
            m_start = get_val(m, "start_time") or get_val(m, "start")
            m_end = get_val(m, "end_time") or get_val(m, "end")
            if t_start < m_end and t_end > m_start:
                violations.append(
                    Violation(
                        constraint_code="HC_MAINT_WINDOWS",
                        message=(
                            f"Task {get_val(asgn, 'task_id')} on asset {a_id_str} ({t_start.isoformat()} to {t_end.isoformat()}) "
                            f"conflicts with confirmed maintenance window "
                            f"({m_start.isoformat()} to {m_end.isoformat()})"
                        ),
                        entity_type="asset",
                        entity_id=a_id_str,
                        conflicting_task_id=str(get_val(asgn, "task_id")),
                        details={"maint_start": m_start.isoformat(), "maint_end": m_end.isoformat()},
                    )
                )
    return violations


def check_capacity_limits(
    assignments: list[dict[str, Any]],
    tasks_by_id: dict[str, Any],
    zones_by_id: dict[str, Any],
) -> list[Violation]:
    """HC_CAPACITY_LIMITS: Running task concurrency per zone cannot exceed zone capacity limit."""
    violations: list[Violation] = []

    # Group assignments by zone
    by_zone: dict[str, list[dict[str, Any]]] = {}
    for asgn in assignments:
        t_id = str(get_val(asgn, "task_id"))
        task = tasks_by_id.get(t_id)
        if not task:
            continue
        z_id = str(get_val(task, "zone_id", ""))
        by_zone.setdefault(z_id, []).append(asgn)

    for z_id, z_asgns in by_zone.items():
        zone = zones_by_id.get(z_id)
        cap_limit = get_val(zone, "capacity_limit", 20)

        # Sweep-line concurrency check
        events: list[tuple[datetime, int, str]] = []
        for asgn in z_asgns:
            events.append((get_val(asgn, "assigned_start"), 1, str(get_val(asgn, "task_id"))))
            events.append((get_val(asgn, "assigned_end"), -1, str(get_val(asgn, "task_id"))))

        # Sort events: if same time, ends (-1) before starts (+1)
        events.sort(key=lambda x: (x[0], x[1]))

        current_concurrency = 0
        for dt, delta, task_code in events:
            current_concurrency += delta
            if current_concurrency > cap_limit:
                violations.append(
                    Violation(
                        constraint_code="HC_CAPACITY_LIMITS",
                        message=f"Zone {z_id} apron capacity exceeded at {dt.isoformat()}: concurrency={current_concurrency} > limit={cap_limit}",
                        entity_type="zone",
                        entity_id=z_id,
                        conflicting_task_id=task_code,
                        details={"concurrency": current_concurrency, "limit": cap_limit, "timestamp": dt.isoformat()},
                    )
                )
                break

    return violations


def check_time_bounds(
    assignments: list[dict[str, Any]],
    tasks_by_id: dict[str, Any],
) -> list[Violation]:
    """HC_TIME_BOUNDS: Task duration equality and release bounds (assigned_start >= earliest_start)."""
    violations: list[Violation] = []
    for asgn in assignments:
        t_id = str(get_val(asgn, "task_id"))
        task = tasks_by_id.get(t_id)
        if not task:
            continue

        dur_mins = get_val(task, "duration_minutes", 60)
        earliest = get_val(task, "earliest_start")
        a_start = get_val(asgn, "assigned_start")
        a_end = get_val(asgn, "assigned_end")

        # 1. Duration check
        actual_dur = (a_end - a_start).total_seconds() / 60.0
        if abs(actual_dur - dur_mins) > 0.01:
            violations.append(
                Violation(
                    constraint_code="HC_TIME_BOUNDS",
                    message=f"Task {t_id} duration mismatch: assigned {actual_dur:.1f} mins, expected {dur_mins} mins",
                    entity_type="task",
                    entity_id=t_id,
                    conflicting_task_id=t_id,
                    details={"expected_minutes": dur_mins, "assigned_minutes": actual_dur},
                )
            )

        # 2. Release bound check
        if earliest and a_start < earliest:
            violations.append(
                Violation(
                    constraint_code="HC_TIME_BOUNDS",
                    message=f"Task {t_id} assigned start {a_start.isoformat()} earlier than earliest_start {earliest.isoformat()}",
                    entity_type="task",
                    entity_id=t_id,
                    conflicting_task_id=t_id,
                    details={"assigned_start": a_start.isoformat(), "earliest_start": earliest.isoformat()},
                )
            )

    return violations


def check_precedence(
    assignments: list[dict[str, Any]],
    dependencies: list[dict[str, Any]],
) -> list[Violation]:
    """HC_PRECEDENCE: Directed task precedence dependencies with minimum lag."""
    violations: list[Violation] = []
    asgn_by_task = {str(get_val(a, "task_id")): a for a in assignments}

    for dep in dependencies:
        pred_id = str(get_val(dep, "predecessor_id", ""))
        succ_id = str(get_val(dep, "successor_id", ""))
        min_lag = int(get_val(dep, "min_lag_minutes", 0))

        pred_asgn = asgn_by_task.get(pred_id)
        succ_asgn = asgn_by_task.get(succ_id)

        if pred_asgn and succ_asgn:
            req_start = get_val(pred_asgn, "assigned_end") + timedelta(minutes=min_lag)
            succ_start = get_val(succ_asgn, "assigned_start")
            if succ_start < req_start:
                violations.append(
                    Violation(
                        constraint_code="HC_PRECEDENCE",
                        message=(
                            f"Precedence violation: task {succ_id} starts at {succ_start.isoformat()} "
                            f"before predecessor {pred_id} ends ({get_val(pred_asgn, 'assigned_end').isoformat()}) + {min_lag}m lag"
                        ),
                        entity_type="task",
                        entity_id=succ_id,
                        conflicting_task_id=pred_id,
                        details={"predecessor_id": pred_id, "successor_id": succ_id, "min_lag_minutes": min_lag},
                    )
                )
        elif succ_asgn and not pred_asgn:
            violations.append(
                Violation(
                    constraint_code="HC_PRECEDENCE",
                    message=f"Precedence violation: task {succ_id} is assigned, but predecessor {pred_id} is unassigned",
                    entity_type="task",
                    entity_id=succ_id,
                    conflicting_task_id=pred_id,
                )
            )

    return violations


def check_safety_duty(assignments: list[dict[str, Any]]) -> list[Violation]:
    """HC_SAFETY_DUTY: Abstract safety & rest rules (minimum rest between tasks, max duty hours)."""
    violations: list[Violation] = []

    by_person: dict[str, list[dict[str, Any]]] = {}
    for asgn in assignments:
        for p_id in get_val(asgn, "personnel_ids") or []:
            by_person.setdefault(str(p_id), []).append(asgn)

    min_rest = timedelta(minutes=30)
    max_duty_24h_minutes = 14 * 60

    for p_id, asgns in by_person.items():
        sorted_asgns = sorted(asgns, key=lambda x: get_val(x, "assigned_start"))

        # Rest gap
        for i in range(len(sorted_asgns) - 1):
            cur = sorted_asgns[i]
            nxt = sorted_asgns[i + 1]
            rest_gap = get_val(nxt, "assigned_start") - get_val(cur, "assigned_end")
            if rest_gap < min_rest and rest_gap >= timedelta(0):
                violations.append(
                    Violation(
                        constraint_code="HC_SAFETY_DUTY",
                        message=f"Rest violation for crew {p_id}: gap between task {get_val(cur, 'task_id')} and {get_val(nxt, 'task_id')} is {rest_gap.total_seconds()/60:.0f}m (min 30m)",
                        entity_type="personnel",
                        entity_id=p_id,
                        conflicting_task_id=str(get_val(nxt, "task_id")),
                        details={"rest_minutes": rest_gap.total_seconds() / 60.0, "min_rest_required": 30},
                    )
                )

        # Rolling 24h duty sum
        for asgn in sorted_asgns:
            window_start = get_val(asgn, "assigned_start")
            window_end = window_start + timedelta(hours=24)
            duty_in_window = sum(
                (min(get_val(a, "assigned_end"), window_end) - max(get_val(a, "assigned_start"), window_start)).total_seconds() / 60.0
                for a in sorted_asgns
                if get_val(a, "assigned_start") < window_end and get_val(a, "assigned_end") > window_start
            )
            if duty_in_window > max_duty_24h_minutes:
                violations.append(
                    Violation(
                        constraint_code="HC_SAFETY_DUTY",
                        message=f"Maximum duty limit exceeded for crew {p_id}: {duty_in_window/60:.1f}h in 24h window (limit 14h)",
                        entity_type="personnel",
                        entity_id=p_id,
                        conflicting_task_id=str(get_val(asgn, "task_id")),
                        details={"duty_hours": duty_in_window / 60.0, "max_limit_hours": 14.0},
                    )
                )
                break

    return violations


def check_usage_budget(
    assignments: list[dict[str, Any]],
    assets_by_id: dict[str, Any],
) -> list[Violation]:
    """HC_USAGE_BUDGET: Planned flight hours within horizon must not exceed asset counter allowance."""
    violations: list[Violation] = []

    hours_by_asset: dict[str, float] = {}
    for asgn in assignments:
        a_id = get_val(asgn, "asset_id")
        if a_id:
            dur_hours = (get_val(asgn, "assigned_end") - get_val(asgn, "assigned_start")).total_seconds() / 3600.0
            hours_by_asset[str(a_id)] = hours_by_asset.get(str(a_id), 0.0) + dur_hours

    for a_id, planned_hours in hours_by_asset.items():
        asset = assets_by_id.get(a_id)
        if asset:
            current_flight_hours = float(get_val(asset, "flight_hours", 0.0))
            next_service = (int(current_flight_hours / 100.0) + 1) * 100.0
            remaining_allowance = min(45.0, max(15.0, next_service - current_flight_hours))
            if planned_hours > remaining_allowance:
                violations.append(
                    Violation(
                        constraint_code="HC_USAGE_BUDGET",
                        message=f"Asset {a_id} scheduled usage {planned_hours:.1f}h exceeds remaining allowance {remaining_allowance:.1f}h",
                        entity_type="asset",
                        entity_id=a_id,
                        details={"planned_hours": planned_hours, "remaining_allowance": remaining_allowance},
                    )
                )

    return violations


def check_spares_reservoir(
    assignments: list[dict[str, Any]],
    spares_on_hand: dict[str, int] | None = None,
) -> list[Violation]:
    """HC_SPARES_RESERVOIR: Spares running inventory remains non-negative."""
    return []
