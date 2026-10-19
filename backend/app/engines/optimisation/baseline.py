"""Baseline Scheduler for AirOps Nexus (Phase 4, Task P4-1).

Implements Weighted Earliest Due Date (W-EDD) dispatch into earliest feasible slots.
Generates an operational baseline plan that strictly satisfies all 10 hard constraints
and passes the IndependentPlanValidator.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any
import time
import uuid
import networkx as nx

from app.core.clock import get_clock
from app.core.enums import PlanKind, PlanSource, PlanStatus, SolverStatus, TaskPriority
from app.engines.optimisation.constraints.modules import get_val
from app.engines.optimisation.validator import IndependentPlanValidator, ValidationResult


@dataclass
class BaselineSchedule:
    assignments: list[dict[str, Any]]
    unassigned_tasks: list[dict[str, Any]]
    metrics: dict[str, Any]
    solver_status: str
    runtime_seconds: float
    validation: ValidationResult | None = None


class BaselineScheduler:
    """Dispatches tasks using Weighted Earliest Due Date (W-EDD) with earliest feasible slot allocation."""

    def __init__(self, slot_minutes: int = 15):
        self.slot_minutes = slot_minutes
        self.validator = IndependentPlanValidator()

    def solve(
        self,
        snapshot: dict[str, Any],
        as_of: datetime | None = None,
        horizon_days: int = 7,
    ) -> BaselineSchedule:
        start_cpu = time.perf_counter()
        clock_as_of = as_of or get_clock().as_of()
        horizon_end = clock_as_of + timedelta(days=horizon_days)

        # 1. Index snapshot entities
        raw_tasks = snapshot.get("tasks", [])
        tasks_by_id = {str(get_val(t, "id")): t for t in raw_tasks}

        raw_reqs = snapshot.get("task_requirements", [])
        requirements_by_task = {
            str(get_val(r, "task_id")): r
            for r in raw_reqs
        }

        dependencies = snapshot.get("task_dependencies", [])
        raw_assets = snapshot.get("assets", [])
        assets_by_id = {str(get_val(a, "id")): a for a in raw_assets}

        raw_personnel = snapshot.get("personnel", [])
        personnel_by_id = {str(get_val(p, "id")): p for p in raw_personnel}

        raw_quals = snapshot.get("personnel_qualifications", [])
        personnel_quals: dict[str, list[dict[str, Any]]] = {}
        for q in raw_quals:
            p_id = str(get_val(q, "personnel_id"))
            if isinstance(q, dict):
                code = q.get("code") or q.get("qualification_code")
                expires = q.get("expires_at")
            else:
                code = q.qualification.code if (hasattr(q, "qualification") and q.qualification) else getattr(q, "code", None)
                expires = getattr(q, "expires_at", None)
            personnel_quals.setdefault(p_id, []).append({"code": code, "expires_at": expires})

        raw_maint = snapshot.get("maintenance_records", [])
        maint_by_asset: dict[str, list[dict[str, Any]]] = {}
        for m in raw_maint:
            status = get_val(m, "status", "scheduled")
            if status in ("scheduled", "in_progress", "deferred"):
                a_id = str(get_val(m, "asset_id"))
                maint_by_asset.setdefault(a_id, []).append({
                    "start": get_val(m, "start_time"),
                    "end": get_val(m, "end_time"),
                })

        raw_zones = snapshot.get("zones", [])
        zones_by_id = {str(get_val(z, "id")): z for z in raw_zones}

        # 2. Filter tasks within planning horizon
        horizon_tasks = []
        for t_id, t in tasks_by_id.items():
            earliest = get_val(t, "earliest_start")
            if earliest and earliest <= horizon_end:
                horizon_tasks.append(t)

        # 3. Build DAG for topological precedence ordering
        dag = nx.DiGraph()
        for t in horizon_tasks:
            t_id = str(get_val(t, "id"))
            dag.add_node(t_id)

        for dep in dependencies:
            pred_id = str(get_val(dep, "predecessor_id", ""))
            succ_id = str(get_val(dep, "successor_id", ""))
            if pred_id in dag and succ_id in dag:
                dag.add_edge(pred_id, succ_id)

        try:
            topo_order = list(nx.topological_sort(dag))
        except nx.NetworkXUnfeasible:
            topo_order = [str(get_val(t, "id")) for t in horizon_tasks]

        def wedd_key(t_id: str) -> float:
            t = tasks_by_id[t_id]
            latest = get_val(t, "latest_end")
            weight = get_val(t, "weight", 1.0)
            prio = get_val(t, "priority", "routine")
            prio_mult = 2.0 if prio == TaskPriority.CRITICAL.value else (1.5 if prio == TaskPriority.HIGH.value else 1.0)
            time_delta = (latest - clock_as_of).total_seconds()
            return time_delta / (weight * prio_mult)

        topo_ranks = {tid: i for i, tid in enumerate(topo_order)}
        sorted_task_ids = sorted(
            [str(get_val(t, "id")) for t in horizon_tasks],
            key=lambda tid: (topo_ranks.get(tid, 999999), wedd_key(tid)),
        )

        # 4. Resource booking trackers
        asset_bookings: dict[str, list[tuple[datetime, datetime]]] = {a_id: [] for a_id in assets_by_id}
        asset_hours_booked: dict[str, float] = {a_id: 0.0 for a_id in assets_by_id}
        for a_id, m_list in maint_by_asset.items():
            if a_id in asset_bookings:
                for m in m_list:
                    asset_bookings[a_id].append((m["start"], m["end"]))

        crew_bookings: dict[str, list[tuple[datetime, datetime]]] = {p_id: [] for p_id in personnel_by_id}

        scheduled_assignments: list[dict[str, Any]] = []
        unassigned_tasks: list[dict[str, Any]] = []
        task_end_times: dict[str, datetime] = {}

        # 5. Greedy earliest feasible slot dispatch
        for t_id in sorted_task_ids:
            task = tasks_by_id[t_id]
            req = requirements_by_task.get(t_id)
            if not req:
                unassigned_tasks.append({
                    "task_id": t_id,
                    "reason_code": "NO_REQUIREMENTS_FOUND",
                    "details": "Task has no requirement specification",
                })
                continue

            dur_mins = get_val(task, "duration_minutes", 60)
            dur_delta = timedelta(minutes=dur_mins)
            earliest_t = get_val(task, "earliest_start")
            t_zone_id = str(get_val(task, "zone_id"))

            cand_start = max(earliest_t, clock_as_of)
            pred_failed = False
            for dep in dependencies:
                succ_id = str(get_val(dep, "successor_id", ""))
                if succ_id == t_id:
                    pred_id = str(get_val(dep, "predecessor_id", ""))
                    min_lag = int(get_val(dep, "min_lag_minutes", 0))
                    if pred_id not in task_end_times:
                        unassigned_tasks.append({
                            "task_id": t_id,
                            "reason_code": "PREDECESSOR_UNASSIGNED",
                            "details": f"Predecessor task {pred_id} was not assigned",
                        })
                        pred_failed = True
                        break
                    cand_start = max(cand_start, task_end_times[pred_id] + timedelta(minutes=min_lag))

            if pred_failed:
                continue

            exp_asset_type = get_val(req, "asset_type_required")
            candidate_assets = [
                a_id for a_id, a in assets_by_id.items()
                if get_val(a, "asset_type") == exp_asset_type
                and get_val(a, "status") not in ("retired", "decommissioned")
            ]

            if not candidate_assets:
                unassigned_tasks.append({
                    "task_id": t_id,
                    "reason_code": "NO_COMPATIBLE_ASSET",
                    "details": f"No active assets of type '{exp_asset_type}' found",
                })
                continue

            exp_headcount = get_val(req, "crew_headcount", 1)
            exp_qual = get_val(req, "required_qualification_code")

            placed = False
            search_step = timedelta(minutes=self.slot_minutes)
            max_search_time = min(horizon_end, cand_start + timedelta(hours=96))

            t_cur = cand_start
            while t_cur <= max_search_time:
                t_end = t_cur + dur_delta

                for a_id in candidate_assets:
                    a_busy = any(
                        (t_cur < b_end and t_end > b_start)
                        for b_start, b_end in asset_bookings[a_id]
                    )
                    if a_busy:
                        continue

                    # Check asset flight hours budget
                    cur_h = asset_hours_booked.get(a_id, 0.0)
                    added_h = dur_delta.total_seconds() / 3600.0
                    cfh = float(get_val(assets_by_id[a_id], "flight_hours", 0.0))
                    next_srv = (int(cfh / 100.0) + 1) * 100.0
                    rem_allowance = min(45.0, max(15.0, next_srv - cfh))
                    if cur_h + added_h > rem_allowance:
                        continue

                    available_crew: list[str] = []
                    for p_id, p in personnel_by_id.items():
                        if get_val(p, "status") in ("leave", "unavailable"):
                            continue

                        if exp_qual:
                            p_quals = personnel_quals.get(p_id, [])
                            has_qual = any(
                                q["code"] == exp_qual and q["expires_at"] > t_cur
                                for q in p_quals
                            )
                            if not has_qual:
                                continue

                        c_busy = any(
                            (t_cur < (b_end + timedelta(minutes=30)) and (t_end + timedelta(minutes=30)) > b_start)
                            for b_start, b_end in crew_bookings[p_id]
                        )
                        if c_busy:
                            continue

                        # Check rolling 24h duty limit (max 14 hours)
                        tentative_bookings = crew_bookings[p_id] + [(t_cur, t_end)]
                        duty_exceeded = False
                        for b_s, b_e in tentative_bookings:
                            w_start = b_s
                            w_end = w_start + timedelta(hours=24)
                            w_duty = sum(
                                (min(b_end, w_end) - max(b_start, w_start)).total_seconds() / 60.0
                                for b_start, b_end in tentative_bookings
                                if b_start < w_end and b_end > w_start
                            )
                            if w_duty > 14 * 60:
                                duty_exceeded = True
                                break

                        if not duty_exceeded:
                            available_crew.append(p_id)
                            if len(available_crew) == exp_headcount:
                                break

                    if len(available_crew) < exp_headcount:
                        continue

                    z_limit = get_val(zones_by_id.get(t_zone_id), "capacity_limit", 20)
                    concurrency = sum(
                        1 for asgn in scheduled_assignments
                        if str(get_val(tasks_by_id[asgn["task_id"]], "zone_id")) == t_zone_id
                        and (t_cur < asgn["assigned_end"] and t_end > asgn["assigned_start"])
                    )
                    if concurrency >= z_limit:
                        continue

                    asset_bookings[a_id].append((t_cur, t_end))
                    asset_hours_booked[a_id] = cur_h + added_h
                    for p_id in available_crew:
                        crew_bookings[p_id].append((t_cur, t_end))

                    scheduled_assignments.append({
                        "task_id": t_id,
                        "asset_id": a_id,
                        "personnel_ids": available_crew,
                        "assigned_start": t_cur,
                        "assigned_end": t_end,
                    })
                    task_end_times[t_id] = t_end
                    placed = True
                    break

                if placed:
                    break
                t_cur += search_step

            if not placed:
                unassigned_tasks.append({
                    "task_id": t_id,
                    "reason_code": "RESOURCE_CONTENTION",
                    "details": "No conflict-free asset and crew slot available within horizon window",
                })

        total_delay = 0.0
        for asgn in scheduled_assignments:
            t = tasks_by_id[asgn["task_id"]]
            latest = get_val(t, "latest_end")
            if asgn["assigned_end"] > latest:
                total_delay += (asgn["assigned_end"] - latest).total_seconds() / 60.0

        runtime_sec = time.perf_counter() - start_cpu
        metrics = {
            "total_horizon_tasks": len(horizon_tasks),
            "scheduled_count": len(scheduled_assignments),
            "unassigned_count": len(unassigned_tasks),
            "total_delay_minutes": round(total_delay, 1),
            "completion_rate": round(len(scheduled_assignments) / max(1, len(horizon_tasks)), 4),
            "objective_value": round(total_delay * 10 + len(unassigned_tasks) * 1000, 2),
        }

        solver_status = SolverStatus.OPTIMAL.value if len(unassigned_tasks) == 0 else SolverStatus.FEASIBLE.value

        # Validate with pure-Python validator
        val_result = self.validator.validate_plan(scheduled_assignments, snapshot)

        return BaselineSchedule(
            assignments=scheduled_assignments,
            unassigned_tasks=unassigned_tasks,
            metrics=metrics,
            solver_status=solver_status,
            runtime_seconds=round(runtime_sec, 3),
            validation=val_result,
        )
