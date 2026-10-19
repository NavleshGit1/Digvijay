"""Google OR-Tools CP-SAT Optimizer for AirOps Nexus (Phase 4, Tasks P4-4 & P4-5).

Encodes operational constraint scheduling with optional intervals, presence literals,
multi-objective integer linear optimization, deterministic single-thread mode (ADR 0004),
honest status mapping (timeout never misreported as infeasible), hints, and progress streaming.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable
import hashlib
import json
import math
import time
import uuid

import ortools
from ortools.sat.python import cp_model

from app.core.clock import get_clock
from app.core.enums import PlanKind, PlanSource, PlanStatus, SolverStatus, TaskPriority
from app.engines.optimisation.baseline import BaselineScheduler
from app.engines.optimisation.constraints.modules import get_val
from app.engines.optimisation.validator import IndependentPlanValidator, ValidationResult


class CPSATProgressCallback(cp_model.CpSolverSolutionCallback):
    """Callback streaming incremental solver solutions and bounds to SSE/Redis."""

    def __init__(self, on_progress: Callable[[dict[str, Any]], None] | None = None):
        super().__init__()
        self.on_progress = on_progress
        self.solution_count = 0
        self.start_time = time.perf_counter()

    def on_solution_callback(self) -> None:
        self.solution_count += 1
        elapsed = time.perf_counter() - self.start_time
        if self.on_progress:
            self.on_progress({
                "solution_count": self.solution_count,
                "objective_value": self.objective_value,
                "best_objective_bound": self.best_objective_bound,
                "elapsed_seconds": round(elapsed, 2),
            })


@dataclass
class CPSATSolverConfig:
    slot_minutes: int = 15
    time_limit_seconds: float = 15.0
    num_search_workers: int = 1  # Deterministic per ADR 0004
    random_seed: int = 42
    use_hints: bool = True
    delay_weight: int = 10
    completion_weight: int = 1000
    churn_weight: int = 50
    balance_weight: int = 5
    buffer_weight: int = 20

    def compute_config_hash(self) -> str:
        s = f"{self.slot_minutes}:{self.time_limit_seconds}:{self.num_search_workers}:{self.random_seed}:{self.delay_weight}:{self.completion_weight}"
        return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


@dataclass
class CPSATSchedule:
    assignments: list[dict[str, Any]]
    unassigned_tasks: list[dict[str, Any]]
    metrics: dict[str, Any]
    solver_status: str
    runtime_seconds: float
    manifest: dict[str, Any]
    validation: ValidationResult | None = None


class CPSATScheduler:
    """Discrete-time Constraint Programming scheduler using Google OR-Tools CP-SAT."""

    def __init__(self, config: CPSATSolverConfig | None = None):
        self.config = config or CPSATSolverConfig()
        self.validator = IndependentPlanValidator()

    def solve(
        self,
        snapshot: dict[str, Any],
        as_of: datetime | None = None,
        horizon_days: int = 7,
        baseline_hint: list[dict[str, Any]] | None = None,
        progress_cb: Callable[[dict[str, Any]], None] | None = None,
    ) -> CPSATSchedule:
        start_cpu = time.perf_counter()
        clock_as_of = as_of or get_clock().as_of()
        horizon_end = clock_as_of + timedelta(days=horizon_days)
        slot_mins = self.config.slot_minutes
        total_slots = int((horizon_end - clock_as_of).total_seconds() / (slot_mins * 60))

        # 1. Normalize snapshot entities
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
                m_start = get_val(m, "start_time")
                m_end = get_val(m, "end_time")
                maint_by_asset.setdefault(a_id, []).append({"start": m_start, "end": m_end})

        raw_zones = snapshot.get("zones", [])
        zones_by_id = {str(get_val(z, "id")): z for z in raw_zones}

        # 2. Filter tasks in planning horizon
        horizon_tasks = []
        for t_id, t in tasks_by_id.items():
            earliest = get_val(t, "earliest_start")
            if earliest and earliest <= horizon_end:
                horizon_tasks.append(t)

        # 3. Instantiate CP-SAT Model
        model = cp_model.CpModel()

        # Variables:
        # task_presence[t_id] = bool var (1 if scheduled, 0 if unassigned)
        # task_start[t_id] = int var in [0, total_slots]
        # task_end[t_id] = int var in [0, total_slots]
        # task_asset_presence[(t_id, a_id)] = bool var
        # intervals_by_asset[a_id] = list of interval vars
        # intervals_by_zone[z_id] = list of (interval, demand)
        task_presence: dict[str, cp_model.IntVar] = {}
        task_start: dict[str, cp_model.IntVar] = {}
        task_end: dict[str, cp_model.IntVar] = {}
        task_asset_presence: dict[tuple[str, str], cp_model.IntVar] = {}
        intervals_by_asset: dict[str, list[cp_model.IntervalVar]] = {a_id: [] for a_id in assets_by_id}
        zone_intervals: dict[str, list[cp_model.IntervalVar]] = {z_id: [] for z_id in zones_by_id}

        # Add fixed maintenance intervals into asset NoOverlap
        for a_id, m_list in maint_by_asset.items():
            if a_id in intervals_by_asset:
                for idx, m in enumerate(m_list):
                    # Clamp maintenance interval to horizon
                    m_s = max(clock_as_of, m["start"])
                    m_e = min(horizon_end, m["end"])
                    if m_e > m_s:
                        s_slot = max(0, int((m_s - clock_as_of).total_seconds() / (slot_mins * 60)))
                        e_slot = min(total_slots, math.ceil((m_e - clock_as_of).total_seconds() / (slot_mins * 60)))
                        dur_slots = max(1, e_slot - s_slot)
                        m_interval = model.NewIntervalVar(
                            s_slot, dur_slots, s_slot + dur_slots, f"maint_{a_id}_{idx}"
                        )
                        intervals_by_asset[a_id].append(m_interval)

        # Create task variables and optional intervals per compatible asset
        for t in horizon_tasks:
            t_id = str(get_val(t, "id"))
            req = requirements_by_task.get(t_id)
            if not req:
                continue

            exp_asset_type = get_val(req, "asset_type_required")
            compat_assets = [
                a_id for a_id, a in assets_by_id.items()
                if get_val(a, "asset_type") == exp_asset_type
                and get_val(a, "status") not in ("retired", "decommissioned")
            ]

            dur_mins = get_val(t, "duration_minutes", 60)
            dur_slots = max(1, math.ceil(dur_mins / slot_mins))

            earliest_t = get_val(t, "earliest_start")
            earliest_slot = max(0, math.ceil((earliest_t - clock_as_of).total_seconds() / (slot_mins * 60)))
            max_start_slot = max(0, total_slots - dur_slots)

            if earliest_slot > max_start_slot or not compat_assets:
                # Cannot be scheduled in horizon
                t_pres = model.NewBoolVar(f"pres_{t_id}")
                model.Add(t_pres == 0)
                task_presence[t_id] = t_pres
                continue

            t_pres = model.NewBoolVar(f"pres_{t_id}")
            task_presence[t_id] = t_pres

            t_st = model.NewIntVar(earliest_slot, max_start_slot, f"st_{t_id}")
            t_en = model.NewIntVar(earliest_slot + dur_slots, total_slots, f"en_{t_id}")
            task_start[t_id] = t_st
            task_end[t_id] = t_en

            asset_pres_literals = []
            for a_id in compat_assets:
                a_pres = model.NewBoolVar(f"pres_{t_id}_{a_id}")
                task_asset_presence[(t_id, a_id)] = a_pres
                asset_pres_literals.append(a_pres)

                interval = model.NewOptionalIntervalVar(
                    t_st, dur_slots, t_en, a_pres, f"interval_{t_id}_{a_id}"
                )
                intervals_by_asset[a_id].append(interval)

            # Task presence is exactly equal to the sum of its asset assignments (at most 1)
            model.Add(sum(asset_pres_literals) == t_pres)

            # Zone capacity tracking
            t_zone_id = str(get_val(t, "zone_id"))
            if t_zone_id in zone_intervals:
                # Main task interval for zone cumulative capacity
                main_interval = model.NewOptionalIntervalVar(
                    t_st, dur_slots, t_en, t_pres, f"zone_int_{t_id}"
                )
                zone_intervals[t_zone_id].append(main_interval)

        # Asset NoOverlap constraints
        for a_id, intervals in intervals_by_asset.items():
            if len(intervals) > 1:
                model.AddNoOverlap(intervals)

        # Zone Capacity Cumulative constraints
        for z_id, intervals in zone_intervals.items():
            if intervals:
                cap_limit = get_val(zones_by_id.get(z_id), "capacity_limit", 20)
                demands = [1] * len(intervals)
                model.AddCumulative(intervals, demands, cap_limit)

        # Precedence constraints (DAG)
        for dep in dependencies:
            pred_id = str(get_val(dep, "predecessor_id", ""))
            succ_id = str(get_val(dep, "successor_id", ""))
            min_lag_mins = int(get_val(dep, "min_lag_minutes", 0))
            min_lag_slots = math.ceil(min_lag_mins / slot_mins)

            if succ_id in task_presence:
                if pred_id not in task_presence:
                    # Predecessor is outside horizon, so successor cannot execute in this horizon
                    model.Add(task_presence[succ_id] == 0)
                else:
                    p_pres = task_presence[pred_id]
                    s_pres = task_presence[succ_id]
                    # If successor is present, predecessor must be present
                    model.Add(p_pres >= s_pres)

                    # Precedence start >= end + lag
                    if pred_id in task_end and succ_id in task_start:
                        model.Add(
                            task_start[succ_id] >= task_end[pred_id] + min_lag_slots
                        ).OnlyEnforceIf([p_pres, s_pres])

        # Usage Budget Constraints per asset
        for a_id in assets_by_id:
            cfh = float(get_val(assets_by_id[a_id], "flight_hours", 0.0))
            next_srv = (int(cfh / 100.0) + 1) * 100.0
            rem_allowance_hours = min(45.0, max(15.0, next_srv - cfh))
            rem_allowance_slots = int((rem_allowance_hours * 60) / slot_mins)

            asset_tasks = [
                (t_id, dur_slots, task_asset_presence[(t_id, a_id)])
                for t in horizon_tasks
                if (t_id := str(get_val(t, "id"))) in tasks_by_id
                and (t_id, a_id) in task_asset_presence
                and (dur_slots := max(1, math.ceil(get_val(t, "duration_minutes", 60) / slot_mins)))
            ]
            if asset_tasks:
                model.Add(
                    sum(dur_s * pres for _, dur_s, pres in asset_tasks) <= rem_allowance_slots
                )

        # Warm-Start Hints from Baseline if available
        if self.config.use_hints and baseline_hint:
            for asgn in baseline_hint:
                b_tid = str(get_val(asgn, "task_id"))
                b_aid = str(get_val(asgn, "asset_id"))
                b_start = get_val(asgn, "assigned_start")
                if b_tid in task_presence and (b_tid, b_aid) in task_asset_presence:
                    model.AddHint(task_presence[b_tid], 1)
                    model.AddHint(task_asset_presence[(b_tid, b_aid)], 1)
                    if b_tid in task_start:
                        slot_idx = max(0, int((b_start - clock_as_of).total_seconds() / (slot_mins * 60)))
                        model.AddHint(task_start[b_tid], slot_idx)

        # Multi-Objective Function Terms
        # 1. Total Delay
        delay_terms = []
        for t in horizon_tasks:
            t_id = str(get_val(t, "id"))
            if t_id in task_end and t_id in task_presence:
                latest_t = get_val(t, "latest_end")
                due_slot = int((latest_t - clock_as_of).total_seconds() / (slot_mins * 60))
                delay_var = model.NewIntVar(0, total_slots, f"delay_{t_id}")
                model.Add(delay_var >= task_end[t_id] - due_slot).OnlyEnforceIf(task_presence[t_id])
                model.Add(delay_var == 0).OnlyEnforceIf(task_presence[t_id].Not())
                delay_terms.append(delay_var)

        # 2. Unassigned task penalties (scaled by priority)
        unassigned_terms = []
        for t in horizon_tasks:
            t_id = str(get_val(t, "id"))
            if t_id in task_presence:
                prio = get_val(t, "priority", "routine")
                mult = 3 if prio == TaskPriority.CRITICAL.value else (2 if prio == TaskPriority.HIGH.value else 1)
                unassigned_terms.append((1 - task_presence[t_id]) * mult)

        # Multi-objective sum
        w_delay = self.config.delay_weight
        w_comp = self.config.completion_weight
        model.Minimize(
            w_delay * sum(delay_terms) + w_comp * sum(unassigned_terms)
        )

        # 4. Solver Execution & Parameters
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.config.time_limit_seconds
        solver.parameters.num_search_workers = self.config.num_search_workers
        solver.parameters.random_seed = self.config.random_seed
        solver.parameters.cp_model_presolve = True

        callback = CPSATProgressCallback(on_progress=progress_cb)
        raw_status = solver.Solve(model, callback)

        solve_runtime = time.perf_counter() - start_cpu

        # 5. Honest Status Mapping
        status_map = {
            cp_model.OPTIMAL: SolverStatus.OPTIMAL.value,
            cp_model.FEASIBLE: SolverStatus.FEASIBLE.value,
            cp_model.INFEASIBLE: SolverStatus.INFEASIBLE.value,
            cp_model.UNKNOWN: SolverStatus.TIMEOUT.value if solve_runtime >= (self.config.time_limit_seconds - 0.5) else SolverStatus.UNKNOWN.value,
            cp_model.MODEL_INVALID: SolverStatus.ERROR.value,
        }
        reported_status = status_map.get(raw_status, SolverStatus.ERROR.value)

        # 6. Extract Solution & Post-Process Crew Assignment
        assignments: list[dict[str, Any]] = []
        unassigned: list[dict[str, Any]] = []

        if raw_status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            # Crew availability trackers
            crew_bookings: dict[str, list[tuple[datetime, datetime]]] = {p_id: [] for p_id in personnel_by_id}

            # Sort tasks by assigned start
            placed_task_ids = [
                t_id for t_id in task_presence
                if solver.Value(task_presence[t_id]) == 1
            ]
            placed_task_ids.sort(key=lambda tid: solver.Value(task_start[tid]))

            for t_id in placed_task_ids:
                task = tasks_by_id[t_id]
                req = requirements_by_task[t_id]
                st_slot = solver.Value(task_start[t_id])
                dur_mins = get_val(task, "duration_minutes", 60)
                t_start = clock_as_of + timedelta(minutes=st_slot * slot_mins)
                t_end = t_start + timedelta(minutes=dur_mins)

                # Determine assigned asset
                assigned_asset_id = None
                for (chk_tid, a_id), a_pres in task_asset_presence.items():
                    if chk_tid == t_id and solver.Value(a_pres) == 1:
                        assigned_asset_id = a_id
                        break

                # Allocate qualified crew satisfying rest gap and rolling duty
                exp_headcount = get_val(req, "crew_headcount", 1)
                exp_qual = get_val(req, "required_qualification_code")

                available_crew: list[str] = []
                for p_id, p in personnel_by_id.items():
                    if get_val(p, "status") in ("leave", "unavailable"):
                        continue

                    if exp_qual:
                        p_quals = personnel_quals.get(p_id, [])
                        has_qual = any(
                            q["code"] == exp_qual and q["expires_at"] > t_start
                            for q in p_quals
                        )
                        if not has_qual:
                            continue

                    c_busy = any(
                        (t_start < (b_end + timedelta(minutes=30)) and (t_end + timedelta(minutes=30)) > b_start)
                        for b_start, b_end in crew_bookings[p_id]
                    )
                    if c_busy:
                        continue

                    # Rolling 24h duty check
                    tentative = crew_bookings[p_id] + [(t_start, t_end)]
                    duty_exceeded = False
                    for b_s, b_e in tentative:
                        w_start = b_s
                        w_end = w_start + timedelta(hours=24)
                        w_duty = sum(
                            (min(b_end, w_end) - max(b_start, w_start)).total_seconds() / 60.0
                            for b_start, b_end in tentative
                            if b_start < w_end and b_end > w_start
                        )
                        if w_duty > 14 * 60:
                            duty_exceeded = True
                            break

                    if not duty_exceeded:
                        available_crew.append(p_id)
                        if len(available_crew) == exp_headcount:
                            break

                if len(available_crew) == exp_headcount:
                    for p_id in available_crew:
                        crew_bookings[p_id].append((t_start, t_end))

                    assignments.append({
                        "task_id": t_id,
                        "asset_id": assigned_asset_id,
                        "personnel_ids": available_crew,
                        "assigned_start": t_start,
                        "assigned_end": t_end,
                    })
                else:
                    unassigned.append({
                        "task_id": t_id,
                        "reason_code": "NO_QUALIFIED_CREW",
                        "details": f"Lacked {exp_headcount} available crew members with rest gap and certifications",
                    })

            # Tasks solver chose not to place
            for t in horizon_tasks:
                t_id = str(get_val(t, "id"))
                if t_id not in task_presence or solver.Value(task_presence[t_id]) == 0:
                    unassigned.append({
                        "task_id": t_id,
                        "reason_code": "SOLVER_UNSCHEDULED",
                        "details": "Omitted by CP-SAT solver to optimize global objective",
                    })

        elif reported_status == SolverStatus.TIMEOUT.value:
            # On timeout without solution, return diagnostic unassigned tasks
            for t in horizon_tasks:
                unassigned.append({
                    "task_id": str(get_val(t, "id")),
                    "reason_code": "SOLVER_TIMEOUT",
                    "details": f"CP-SAT reached {self.config.time_limit_seconds}s limit without provable solution",
                })
        elif reported_status == SolverStatus.INFEASIBLE.value:
            for t in horizon_tasks:
                unassigned.append({
                    "task_id": str(get_val(t, "id")),
                    "reason_code": "MODEL_INFEASIBLE",
                    "details": "Contradictory constraints rendered schedule mathematically infeasible",
                })

        # Calculate metrics
        total_delay = 0.0
        for asgn in assignments:
            t = tasks_by_id[asgn["task_id"]]
            latest = get_val(t, "latest_end")
            if asgn["assigned_end"] > latest:
                total_delay += (asgn["assigned_end"] - latest).total_seconds() / 60.0

        metrics = {
            "total_horizon_tasks": len(horizon_tasks),
            "scheduled_count": len(assignments),
            "unassigned_count": len(unassigned),
            "total_delay_minutes": round(total_delay, 1),
            "completion_rate": round(len(assignments) / max(1, len(horizon_tasks)), 4),
            "objective_value": round(solver.ObjectiveValue() if raw_status in (cp_model.OPTIMAL, cp_model.FEASIBLE) else 0.0, 2),
            "best_bound": round(solver.BestObjectiveBound() if raw_status in (cp_model.OPTIMAL, cp_model.FEASIBLE) else 0.0, 2),
        }

        # Run Independent Pure-Python Validator
        val_result = self.validator.validate_plan(assignments, snapshot)

        manifest = {
            "num_search_workers": self.config.num_search_workers,
            "random_seed": self.config.random_seed,
            "time_limit_seconds": self.config.time_limit_seconds,
            "solver_version": f"OR-Tools {ortools.__version__}",
            "reproducible": self.config.num_search_workers == 1,
            "config_hash": self.config.compute_config_hash(),
            "best_objective_bound": metrics["best_bound"],
            "optimality_gap": round(abs(metrics["objective_value"] - metrics["best_bound"]), 2) if metrics["best_bound"] else 0.0,
        }

        return CPSATSchedule(
            assignments=assignments,
            unassigned_tasks=unassigned,
            metrics=metrics,
            solver_status=reported_status,
            runtime_seconds=round(solve_runtime, 3),
            manifest=manifest,
            validation=val_result,
        )
