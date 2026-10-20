"""Operational Impact Detector using NetworkX Graph Analysis (Phase 6, Tasks P6-3 & P6-13).

Constructs an in-memory directed dependency graph across:
- Aircraft assets and maintenance intervals
- Tasks and acyclic precedence dependencies (DAG)
- Personnel assignments and rest constraints
- Spare parts inventories and resupply deliveries

Identifies directly affected assignments, cascading ripple effects across
downstream sorties, personnel conflicts, and evaluates whether the current
approved plan requires immediate replanning.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
import uuid

import networkx as nx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import get_clock
from app.engines.optimisation.constraints.modules import get_val
from app.models.logistics import MaintenancePartRequirement, MaintenanceRule, Part, ResupplyOrder, SparesInventory
from app.models.operations import MaintenanceRecord, Task, TaskDependency, TaskRequirement
from app.models.plans import Plan, PlanAssignment, PlanVersion
from app.models.resources import Asset, Personnel


@dataclass
class ImpactedTaskDetail:
    task_id: str
    task_code: str
    impact_type: str  # "direct_overlap", "cascading_precedence", "crew_conflict", "spares_shortage"
    scheduled_start: str
    scheduled_end: str
    assigned_asset: str | None
    assigned_crew: list[str]
    delay_delta_minutes: float
    description: str


@dataclass
class ImpactAssessmentResult:
    maintenance_id: str
    asset_id: str
    asset_tail: str
    delay_minutes: float
    original_window_start: str
    original_window_end: str
    extended_window_end: str
    directly_affected_tasks: list[ImpactedTaskDetail]
    cascading_affected_tasks: list[ImpactedTaskDetail]
    affected_crew_count: int
    affected_crew_names: list[str]
    spares_impacted: list[dict[str, Any]]
    plan_invalidated: bool
    violations_detected: list[dict[str, Any]]
    replan_recommended: bool
    recommendation_reason: str
    graph_nodes_count: int
    graph_edges_count: int
    as_of: str = field(default_factory=lambda: get_clock().now().isoformat())

    @property
    def record_id(self) -> str:
        return self.maintenance_id

    @property
    def directly_affected_count(self) -> int:
        return len(self.directly_affected_tasks)

    @property
    def cascading_affected_count(self) -> int:
        return len(self.cascading_affected_tasks)

    @property
    def affected_tasks(self) -> list[ImpactedTaskDetail]:
        return self.directly_affected_tasks + self.cascading_affected_tasks

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.maintenance_id,
            "maintenance_id": self.maintenance_id,
            "asset_id": self.asset_id,
            "asset_identifier": self.asset_tail,
            "asset_tail": self.asset_tail,
            "delay_minutes": self.delay_minutes,
            "original_window_start": self.original_window_start,
            "original_window_end": self.original_window_end,
            "extended_window_end": self.extended_window_end,
            "extended_scheduled_end": self.extended_window_end,
            "directly_affected_count": len(self.directly_affected_tasks),
            "cascading_affected_count": len(self.cascading_affected_tasks),
            "crew_conflicts_count": self.affected_crew_count,
            "directly_affected_tasks": [t.__dict__ for t in self.directly_affected_tasks],
            "cascading_affected_tasks": [t.__dict__ for t in self.cascading_affected_tasks],
            "affected_tasks": [t.__dict__ for t in (self.directly_affected_tasks + self.cascading_affected_tasks)],
            "affected_crew_count": self.affected_crew_count,
            "affected_crew_names": self.affected_crew_names,
            "spares_impacted": self.spares_impacted,
            "plan_invalidated": self.plan_invalidated,
            "violations_detected": self.violations_detected,
            "replan_recommended": self.replan_recommended,
            "recommendation_reason": self.recommendation_reason,
            "graph_nodes_count": self.graph_nodes_count,
            "graph_edges_count": self.graph_edges_count,
            "as_of": self.as_of,
        }


class OperationalImpactDetector:
    """NetworkX-based graph analyzer detecting disruption propagation across operational assets."""

    def __init__(self, db: Session, as_of: datetime | None = None):
        self.db = db
        self.as_of = as_of or get_clock().as_of()
        self.graph = nx.DiGraph()

    def build_operational_graph(
        self,
        approved_version: PlanVersion | None = None,
    ) -> nx.DiGraph:
        """Constructs multi-entity dependency graph in NetworkX."""
        self.graph.clear()

        # 1. Add Asset Nodes
        assets = self.db.execute(select(Asset)).scalars().all()
        for a in assets:
            self.graph.add_node(
                f"asset:{a.id}",
                node_type="asset",
                identifier=a.identifier,
                model_name=a.model_name,
                status=a.status,
            )

        # 2. Add Task Nodes and Precedence Edges (DAG)
        tasks = self.db.execute(select(Task)).scalars().all()
        for t in tasks:
            self.graph.add_node(
                f"task:{t.id}",
                node_type="task",
                code=t.code,
                priority=t.priority,
                earliest_start=t.earliest_start,
                latest_end=t.latest_end,
                duration_minutes=t.duration_minutes,
            )

        dependencies = self.db.execute(select(TaskDependency)).scalars().all()
        for dep in dependencies:
            self.graph.add_edge(
                f"task:{dep.predecessor_id}",
                f"task:{dep.successor_id}",
                edge_type="precedence",
                min_lag_minutes=dep.min_lag_minutes,
            )

        # 3. Add Personnel Nodes
        crew = self.db.execute(select(Personnel)).scalars().all()
        for p in crew:
            self.graph.add_node(
                f"personnel:{p.id}",
                node_type="personnel",
                callsign=p.callsign,
                name=f"{p.name} ({p.callsign})" if p.callsign else p.name,
            )

        # 4. Add Active Maintenance Nodes
        maint_records = self.db.execute(select(MaintenanceRecord)).scalars().all()
        for m in maint_records:
            m_node = f"maint:{m.id}"
            self.graph.add_node(
                m_node,
                node_type="maintenance",
                category=m.category,
                start_time=m.start_time,
                end_time=m.end_time,
                status=m.status,
            )
            # Connect Asset to Maintenance
            self.graph.add_edge(f"asset:{m.asset_id}", m_node, edge_type="committed_maintenance")

        # 5. Add Plan Assignment Edges from Approved Plan
        if approved_version:
            assignments = (
                self.db.execute(
                    select(PlanAssignment).where(PlanAssignment.plan_version_id == approved_version.id)
                )
                .scalars()
                .all()
            )
            for asgn in assignments:
                t_node = f"task:{asgn.task_id}"
                if asgn.asset_id:
                    self.graph.add_edge(
                        f"asset:{asgn.asset_id}",
                        t_node,
                        edge_type="assigned_asset",
                        assigned_start=asgn.assigned_start,
                        assigned_end=asgn.assigned_end,
                        is_locked=asgn.is_locked,
                    )
                if asgn.personnel_ids:
                    for p_id in asgn.personnel_ids:
                        self.graph.add_edge(
                            f"personnel:{p_id}",
                            t_node,
                            edge_type="assigned_crew",
                            assigned_start=asgn.assigned_start,
                            assigned_end=asgn.assigned_end,
                        )

        # 6. Spares Inventory Requirements
        rules_by_id = {r.id: r for r in self.db.execute(select(MaintenanceRule)).scalars().all()}
        part_reqs = self.db.execute(select(MaintenancePartRequirement)).scalars().all()
        for pr in part_reqs:
            p_node = f"part:{pr.part_id}"
            if not self.graph.has_node(p_node):
                self.graph.add_node(p_node, node_type="part")
            rule = rules_by_id.get(pr.rule_id)
            if rule:
                for m in maint_records:
                    if m.category == rule.category:
                        self.graph.add_edge(p_node, f"maint:{m.id}", edge_type="spares_requirement", quantity=pr.quantity_required)

        return self.graph

    def detect_maintenance_impact(
        self,
        maintenance_id: uuid.UUID,
        delay_minutes: float = 120.0,
    ) -> ImpactAssessmentResult:
        """Evaluates operational ripple effect of a maintenance window delay."""
        maint = self.db.get(MaintenanceRecord, maintenance_id)
        if not maint:
            raise ValueError(f"Maintenance record '{maintenance_id}' not found")

        asset = self.db.get(Asset, maint.asset_id)
        asset_tail = asset.identifier if asset else "UNKNOWN"

        # Determine currently approved plan version
        approved_version = None
        plan = self.db.execute(select(Plan)).scalars().first()
        if plan and plan.current_approved_version_id:
            approved_version = self.db.get(PlanVersion, plan.current_approved_version_id)

        # Build graph
        self.build_operational_graph(approved_version)

        orig_start = maint.start_time
        orig_end = maint.end_time
        ext_end = orig_end + timedelta(minutes=delay_minutes)

        directly_affected: list[ImpactedTaskDetail] = []
        cascading_affected: list[ImpactedTaskDetail] = []
        crew_impacted_set: set[str] = set()
        violations: list[dict[str, Any]] = []

        if not approved_version:
            return ImpactAssessmentResult(
                maintenance_id=str(maintenance_id),
                asset_id=str(maint.asset_id),
                asset_tail=asset_tail,
                delay_minutes=delay_minutes,
                original_window_start=orig_start.isoformat(),
                original_window_end=orig_end.isoformat(),
                extended_window_end=ext_end.isoformat(),
                directly_affected_tasks=[],
                cascading_affected_tasks=[],
                affected_crew_count=0,
                affected_crew_names=[],
                spares_impacted=[],
                plan_invalidated=False,
                violations_detected=[],
                replan_recommended=False,
                recommendation_reason="No currently approved baseline plan to evaluate against.",
                graph_nodes_count=self.graph.number_of_nodes(),
                graph_edges_count=self.graph.number_of_edges(),
            )

        # Get all assignments for this approved version
        assignments = (
            self.db.execute(
                select(PlanAssignment).where(PlanAssignment.plan_version_id == approved_version.id)
            )
            .scalars()
            .all()
        )
        asgn_by_task = {a.task_id: a for a in assignments}
        tasks_by_id = {t.id: t for t in self.db.execute(select(Task)).scalars().all()}
        crew_by_id = {p.id: p for p in self.db.execute(select(Personnel)).scalars().all()}

        # 1. Directly affected tasks assigned to this asset overlapping with extended window
        direct_task_ids: set[uuid.UUID] = set()
        for asgn in assignments:
            if asgn.asset_id == maint.asset_id:
                # Check overlap with extended window [orig_start, ext_end]
                if asgn.assigned_start < ext_end and asgn.assigned_end > orig_start:
                    direct_task_ids.add(asgn.task_id)
                    task = tasks_by_id.get(asgn.task_id)
                    task_code = task.code if task else str(asgn.task_id)[:8]

                    # Crew names
                    crew_names: list[str] = []
                    if asgn.personnel_ids:
                        for p_id in asgn.personnel_ids:
                            p = crew_by_id.get(p_id)
                            if p:
                                c_name = f"{p.name} ({p.callsign})"
                                crew_names.append(c_name)
                                crew_impacted_set.add(c_name)

                    # Compute overlap delta
                    overlap_mins = min(
                        (ext_end - asgn.assigned_start).total_seconds() / 60.0,
                        delay_minutes,
                    )

                    directly_affected.append(
                        ImpactedTaskDetail(
                            task_id=str(asgn.task_id),
                            task_code=task_code,
                            impact_type="direct_overlap",
                            scheduled_start=asgn.assigned_start.isoformat(),
                            scheduled_end=asgn.assigned_end.isoformat(),
                            assigned_asset=asset_tail,
                            assigned_crew=crew_names,
                            delay_delta_minutes=round(overlap_mins, 1),
                            description=(
                                f"Task {task_code} conflicts directly with extended maintenance "
                                f"on asset {asset_tail} (delayed to {ext_end.strftime('%Y-%m-%d %H:%M UTC')})."
                            ),
                        )
                    )

                    violations.append({
                        "constraint_code": "HC_MAINT_WINDOWS",
                        "message": (
                            f"Hard maintenance collision: Asset {asset_tail} is in delayed maintenance "
                            f"until {ext_end.isoformat()} but task {task_code} is assigned starting at "
                            f"{asgn.assigned_start.isoformat()}."
                        ),
                        "task_id": str(asgn.task_id),
                        "asset_id": str(maint.asset_id),
                    })

        # 2. Cascading ripple effects via NetworkX DAG descendants
        cascading_task_ids: set[uuid.UUID] = set()
        for d_tid in direct_task_ids:
            node_key = f"task:{d_tid}"
            if self.graph.has_node(node_key):
                # Traverse all successors in the DAG
                descendant_nodes = nx.descendants(self.graph, node_key)
                for desc_node in descendant_nodes:
                    if desc_node.startswith("task:"):
                        c_tid = uuid.UUID(desc_node.split(":")[1])
                        if c_tid not in direct_task_ids and c_tid not in cascading_task_ids:
                            cascading_task_ids.add(c_tid)
                            c_asgn = asgn_by_task.get(c_tid)
                            c_task = tasks_by_id.get(c_tid)
                            c_code = c_task.code if c_task else str(c_tid)[:8]

                            c_crew: list[str] = []
                            if c_asgn and c_asgn.personnel_ids:
                                for p_id in c_asgn.personnel_ids:
                                    p = crew_by_id.get(p_id)
                                    if p:
                                        c_name = f"{p.name} ({p.callsign})"
                                        c_crew.append(c_name)
                                        crew_impacted_set.add(c_name)

                            c_asset_tail = "Unassigned"
                            if c_asgn and c_asgn.asset_id:
                                ca = self.db.get(Asset, c_asgn.asset_id)
                                if ca:
                                    c_asset_tail = ca.identifier

                            start_str = c_asgn.assigned_start.isoformat() if c_asgn else "N/A"
                            end_str = c_asgn.assigned_end.isoformat() if c_asgn else "N/A"

                            cascading_affected.append(
                                ImpactedTaskDetail(
                                    task_id=str(c_tid),
                                    task_code=c_code,
                                    impact_type="cascading_precedence",
                                    scheduled_start=start_str,
                                    scheduled_end=end_str,
                                    assigned_asset=c_asset_tail,
                                    assigned_crew=c_crew,
                                    delay_delta_minutes=round(delay_minutes, 1),
                                    description=(
                                        f"Downstream sortie {c_code} depends on delayed predecessor "
                                        f"and may suffer cascaded schedule slippage."
                                    ),
                                )
                            )

                            violations.append({
                                "constraint_code": "HC_PRECEDENCE",
                                "message": (
                                    f"Precedence ripple: Downstream task {c_code} depends on delayed "
                                    f"upstream sortie."
                                ),
                                "task_id": str(c_tid),
                            })

        # 3. Spares inventory impact
        spares_impacted: list[dict[str, Any]] = []
        spares_list = self.db.execute(select(SparesInventory)).scalars().all()
        parts_by_id = {p.id: p for p in self.db.execute(select(Part)).scalars().all()}
        for sp in spares_list:
            if sp.on_hand <= sp.minimum_safety_level:
                part = parts_by_id.get(sp.part_id)
                spares_impacted.append({
                    "part_id": str(sp.part_id),
                    "part_name": part.name if part else "Unknown Part",
                    "part_number": part.part_number if part else "N/A",
                    "on_hand": sp.on_hand,
                    "safety_stock": sp.minimum_safety_level,
                    "status": "critical_low" if sp.on_hand == 0 else "below_safety_stock",
                })

        plan_invalidated = len(violations) > 0
        replan_recommended = len(direct_task_ids) > 0 or len(cascading_task_ids) > 0

        reason = (
            f"Maintenance delay of {delay_minutes:.0f} mins on {asset_tail} causes "
            f"{len(directly_affected)} direct work collision(s) and {len(cascading_affected)} "
            f"cascading precedence disruption(s). Immediate replanning recommended."
            if replan_recommended
            else "Maintenance delay does not collide with scheduled commitments."
        )

        return ImpactAssessmentResult(
            maintenance_id=str(maintenance_id),
            asset_id=str(maint.asset_id),
            asset_tail=asset_tail,
            delay_minutes=delay_minutes,
            original_window_start=orig_start.isoformat(),
            original_window_end=orig_end.isoformat(),
            extended_window_end=ext_end.isoformat(),
            directly_affected_tasks=directly_affected,
            cascading_affected_tasks=cascading_affected,
            affected_crew_count=len(crew_impacted_set),
            affected_crew_names=sorted(list(crew_impacted_set)),
            spares_impacted=spares_impacted,
            plan_invalidated=plan_invalidated,
            violations_detected=violations,
            replan_recommended=replan_recommended,
            recommendation_reason=reason,
            graph_nodes_count=self.graph.number_of_nodes(),
            graph_edges_count=self.graph.number_of_edges(),
        )
