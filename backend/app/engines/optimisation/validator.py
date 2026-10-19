"""Independent Pure-Python Plan Validator (Phase 4, Task P4-3).

This module contains ZERO imports from OR-Tools or solver internals.
It serves as the definitive, isolated arbiter of operational safety and validity.
Evaluates all 10 operational invariants defined in docs/constraint-definitions.md.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import uuid

from app.core.clock import get_clock
from app.engines.optimisation.constraints.modules import (
    Violation,
    get_val,
    check_resource_avail,
    check_no_overlap,
    check_qualifications,
    check_maint_windows,
    check_capacity_limits,
    check_time_bounds,
    check_precedence,
    check_safety_duty,
    check_usage_budget,
    check_spares_reservoir,
)


@dataclass
class ValidationResult:
    is_valid: bool
    violation_count: int
    violations: list[dict[str, Any]]
    binding_constraints: list[dict[str, Any]]
    summary: str
    validated_at: datetime = field(default_factory=lambda: get_clock().now())

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "violation_count": self.violation_count,
            "violations": self.violations,
            "binding_constraints": self.binding_constraints,
            "summary": self.summary,
            "validated_at": self.validated_at.isoformat(),
        }


class IndependentPlanValidator:
    """Pure-Python independent validator for operational schedules."""

    def __init__(self):
        pass

    def validate_plan(
        self,
        assignments: list[dict[str, Any]],
        snapshot: dict[str, Any],
    ) -> ValidationResult:
        """Evaluates all 10 hard constraints against an assignment schedule and dataset snapshot.

        Zero solver dependencies. Completely pure Python.
        """
        # 1. Normalize tasks
        raw_tasks = snapshot.get("tasks", [])
        tasks_by_id: dict[str, Any] = {str(get_val(t, "id")): t for t in raw_tasks}

        # 2. Normalize requirements
        raw_reqs = snapshot.get("task_requirements", [])
        requirements_by_task: dict[str, Any] = {str(get_val(r, "task_id")): r for r in raw_reqs}

        # 3. Normalize dependencies
        dependencies = snapshot.get("task_dependencies", [])

        # 4. Normalize assets
        raw_assets = snapshot.get("assets", [])
        assets_by_id: dict[str, Any] = {str(get_val(a, "id")): a for a in raw_assets}

        # 5. Normalize personnel
        raw_personnel = snapshot.get("personnel", [])
        personnel_by_id: dict[str, Any] = {str(get_val(p, "id")): p for p in raw_personnel}

        # 6. Normalize personnel qualifications
        raw_quals = snapshot.get("personnel_qualifications", [])
        personnel_quals_by_person: dict[str, list[dict[str, Any]]] = {}
        for q in raw_quals:
            p_id = str(get_val(q, "personnel_id"))
            if isinstance(q, dict):
                code = q.get("code") or q.get("qualification_code")
                expires = q.get("expires_at")
            else:
                code = q.qualification.code if (hasattr(q, "qualification") and q.qualification) else getattr(q, "code", None)
                expires = getattr(q, "expires_at", None)
            q_dict = {
                "qualification_code": code,
                "expires_at": expires,
            }
            personnel_quals_by_person.setdefault(p_id, []).append(q_dict)

        # 7. Normalize maintenance records
        raw_maint = snapshot.get("maintenance_records", [])
        maintenance_by_asset: dict[str, list[dict[str, Any]]] = {}
        for m in raw_maint:
            a_id = str(get_val(m, "asset_id"))
            status = get_val(m, "status", "scheduled")
            if status in ("scheduled", "in_progress", "deferred"):
                maintenance_by_asset.setdefault(a_id, []).append({
                    "id": str(get_val(m, "id", "")),
                    "start_time": get_val(m, "start_time"),
                    "end_time": get_val(m, "end_time"),
                    "category": get_val(m, "category"),
                })

        # 8. Normalize zones
        raw_zones = snapshot.get("zones", [])
        zones_by_id: dict[str, Any] = {str(get_val(z, "id")): z for z in raw_zones}

        # Normalize assignments to plain dicts with datetime objects
        norm_assignments: list[dict[str, Any]] = []
        for asgn in assignments:
            norm_assignments.append({
                "task_id": str(get_val(asgn, "task_id")),
                "asset_id": str(get_val(asgn, "asset_id")) if get_val(asgn, "asset_id") else None,
                "personnel_ids": [str(p) for p in (get_val(asgn, "personnel_ids") or [])],
                "assigned_start": get_val(asgn, "assigned_start"),
                "assigned_end": get_val(asgn, "assigned_end"),
            })

        # Run all 10 Invariants
        violations: list[Violation] = []
        violations.extend(check_resource_avail(norm_assignments, assets_by_id, personnel_by_id))
        violations.extend(check_no_overlap(norm_assignments))
        violations.extend(check_qualifications(norm_assignments, tasks_by_id, requirements_by_task, assets_by_id, personnel_quals_by_person))
        violations.extend(check_maint_windows(norm_assignments, maintenance_by_asset))
        violations.extend(check_capacity_limits(norm_assignments, tasks_by_id, zones_by_id))
        violations.extend(check_time_bounds(norm_assignments, tasks_by_id))
        violations.extend(check_precedence(norm_assignments, dependencies))
        violations.extend(check_safety_duty(norm_assignments))
        violations.extend(check_usage_budget(norm_assignments, assets_by_id))
        violations.extend(check_spares_reservoir(norm_assignments))

        # Compute binding constraints (zero-slack instances)
        binding_constraints = self._compute_binding_constraints(
            norm_assignments, tasks_by_id, dependencies
        )

        is_valid = len(violations) == 0
        summary = (
            f"Validation PASSED: 0 violations across {len(norm_assignments)} assignments. {len(binding_constraints)} binding constraints identified."
            if is_valid
            else f"Validation FAILED: {len(violations)} violations detected."
        )

        return ValidationResult(
            is_valid=is_valid,
            violation_count=len(violations),
            violations=[v.to_dict() for v in violations],
            binding_constraints=binding_constraints,
            summary=summary,
        )

    def _compute_binding_constraints(
        self,
        assignments: list[dict[str, Any]],
        tasks_by_id: dict[str, Any],
        dependencies: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Identifies zero-slack instances among active hard constraints."""
        bindings: list[dict[str, Any]] = []

        # 1. Earliest Start release bound binding (slack == 0)
        for asgn in assignments:
            t_id = asgn["task_id"]
            task = tasks_by_id.get(t_id)
            if task:
                earliest = get_val(task, "earliest_start")
                if earliest and asgn["assigned_start"] == earliest:
                    bindings.append({
                        "constraint_code": "HC_TIME_BOUNDS_RELEASE",
                        "entity_type": "task",
                        "entity_id": t_id,
                        "slack_minutes": 0,
                        "description": f"Task {t_id} scheduled exactly at release date {earliest.isoformat()}",
                    })

        # 2. Precedence binding (slack == 0)
        asgn_by_task = {a["task_id"]: a for a in assignments}
        for dep in dependencies:
            pred_id = str(get_val(dep, "predecessor_id", ""))
            succ_id = str(get_val(dep, "successor_id", ""))
            min_lag = int(get_val(dep, "min_lag_minutes", 0))

            pred_asgn = asgn_by_task.get(pred_id)
            succ_asgn = asgn_by_task.get(succ_id)
            if pred_asgn and succ_asgn:
                gap_minutes = (succ_asgn["assigned_start"] - pred_asgn["assigned_end"]).total_seconds() / 60.0
                if abs(gap_minutes - min_lag) < 0.01:
                    bindings.append({
                        "constraint_code": "HC_PRECEDENCE",
                        "entity_type": "dependency",
                        "entity_id": f"{pred_id}->{succ_id}",
                        "slack_minutes": 0,
                        "description": f"Precedence lag between {pred_id} and {succ_id} is exactly binding at {min_lag}m",
                    })

        # 3. Asset back-to-back turnaround (slack == 0)
        by_asset: dict[str, list[dict[str, Any]]] = {}
        for asgn in assignments:
            if asgn.get("asset_id"):
                by_asset.setdefault(asgn["asset_id"], []).append(asgn)

        for a_id, asgns in by_asset.items():
            sorted_asgns = sorted(asgns, key=lambda x: x["assigned_start"])
            for i in range(len(sorted_asgns) - 1):
                cur = sorted_asgns[i]
                nxt = sorted_asgns[i + 1]
                gap_minutes = (nxt["assigned_start"] - cur["assigned_end"]).total_seconds() / 60.0
                if abs(gap_minutes) < 0.01:
                    bindings.append({
                        "constraint_code": "HC_NO_OVERLAP_ASSET",
                        "entity_type": "asset",
                        "entity_id": a_id,
                        "slack_minutes": 0,
                        "description": f"Asset {a_id} turnaround between task {cur['task_id']} and {nxt['task_id']} is binding with 0m slack",
                    })

        return bindings
