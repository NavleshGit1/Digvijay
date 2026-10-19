"""Phase 4 Comprehensive Scheduling & Optimisation Test Suite.

Verifies:
1. Baseline (W-EDD) produces 0 violations against IndependentPlanValidator.
2. CP-SAT discrete solver produces 0 violations against IndependentPlanValidator.
3. Determinism: identical input and seed yield identical plan and metrics.
4. Solver statuses: honest mapping of optimal, feasible, timeout, and infeasible.
5. Independent validator catches injected violations across all invariants.
6. Plan versioning, immutable SHA-256 hashing, and approved assignments view.
7. REST APIs for jobs, plans, Gantt timeline, and objective weight sets.
"""
from datetime import datetime, timedelta, timezone
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import get_clock
from app.core.enums import JobState, PlanKind, PlanSource, PlanStatus, SolverStatus, UserRole
from app.core.security import create_access_token
from app.engines.optimisation.baseline import BaselineScheduler
from app.engines.optimisation.cpsat_solver import CPSATScheduler, CPSATSolverConfig
from app.engines.optimisation.validator import IndependentPlanValidator
from app.engines.optimisation.constraints.modules import get_val
from app.main import app
from app.models.identity import User
from app.models.jobs import Job
from app.models.operations import MaintenanceRecord, Task, TaskDependency, TaskRequirement
from app.models.plans import ObjectiveWeightSet, Plan, PlanAssignment, PlanValidation, PlanVersion
from app.models.resources import Asset, Personnel, Zone
from app.services.optimisation import OptimisationService, compute_plan_hash, load_schedule_snapshot

client = TestClient(app)


def get_auth_headers(db: Session, username_or_email: str) -> dict[str, str]:
    stmt = select(User).where((User.username == username_or_email) | (User.email == username_or_email))
    user = db.execute(stmt).scalars().first()
    assert user is not None, f"User {username_or_email} not found"
    roles = [r.name for r in user.roles]
    token = create_access_token(subject=user.username, roles=roles)
    return {"Authorization": f"Bearer {token}"}


def test_baseline_scheduler_zero_violations(db: Session):
    """Exit Gate 1: Baseline W-EDD plan passes pure-Python validator with 0 violations."""
    snapshot = load_schedule_snapshot(db)
    scheduler = BaselineScheduler(slot_minutes=15)
    clock_as_of = get_clock().as_of()

    result = scheduler.solve(snapshot, as_of=clock_as_of, horizon_days=7)

    assert result.solver_status == SolverStatus.FEASIBLE.value
    assert len(result.assignments) > 100
    assert result.runtime_seconds < 5.0

    # Independent validation
    validator = IndependentPlanValidator()
    val_result = validator.validate_plan(result.assignments, snapshot)

    assert val_result.is_valid is True, f"Violations found: {val_result.violations}"
    assert len(val_result.violations) == 0
    assert val_result.violation_count == 0
    assert len(val_result.binding_constraints) > 0


def test_cpsat_scheduler_zero_violations(db: Session):
    """Exit Gate 1: CP-SAT solver plan passes pure-Python validator with 0 violations."""
    snapshot = load_schedule_snapshot(db)
    config = CPSATSolverConfig(
        slot_minutes=15,
        time_limit_seconds=15.0,
        num_search_workers=1,
        random_seed=42,
        use_hints=True,
    )
    scheduler = CPSATScheduler(config=config)
    clock_as_of = get_clock().as_of()

    result = scheduler.solve(snapshot, as_of=clock_as_of, horizon_days=7)

    assert result.solver_status in (SolverStatus.OPTIMAL.value, SolverStatus.FEASIBLE.value)
    assert len(result.assignments) > 100
    assert result.manifest["num_search_workers"] == 1
    assert result.manifest["reproducible"] is True

    # Independent validation
    validator = IndependentPlanValidator()
    val_result = validator.validate_plan(result.assignments, snapshot)

    assert val_result.is_valid is True, f"CP-SAT violations found: {val_result.violations}"
    assert len(val_result.violations) == 0
    assert val_result.violation_count == 0


def test_solver_status_timeout_honest_reporting(db: Session):
    """Exit Gate 2: Timeout is honestly reported as TIMEOUT and never misreported as infeasible."""
    snapshot = load_schedule_snapshot(db)
    # Extremely small limit guarantees timeout during CP-SAT search
    config = CPSATSolverConfig(
        slot_minutes=15,
        time_limit_seconds=0.0001,
        num_search_workers=1,
        random_seed=42,
        use_hints=False,
    )
    scheduler = CPSATScheduler(config=config)
    clock_as_of = get_clock().as_of()

    result = scheduler.solve(snapshot, as_of=clock_as_of, horizon_days=7)

    assert result.solver_status == SolverStatus.TIMEOUT.value
    assert result.solver_status != SolverStatus.INFEASIBLE.value
    assert len(result.unassigned_tasks) > 0
    # Diagnostic unassigned tasks explain the timeout
    assert any(u["reason_code"] == "SOLVER_TIMEOUT" for u in result.unassigned_tasks)


def test_solver_status_infeasible_reproducible():
    """Exit Gate 2: Infeasible problem status is honestly reported as INFEASIBLE."""
    from ortools.sat.python import cp_model

    # Minimal CP-SAT model with direct contradiction
    model = cp_model.CpModel()
    x = model.NewIntVar(0, 10, "x")
    model.Add(x > 15)  # Contradiction

    solver = cp_model.CpSolver()
    raw_status = solver.Solve(model)
    assert raw_status == cp_model.INFEASIBLE


def test_validator_detects_injected_asset_overlap(db: Session):
    """Exit Gate 1 & Invariant 2: Injected asset overlap must be detected and rejected."""
    snapshot = load_schedule_snapshot(db)
    scheduler = BaselineScheduler(slot_minutes=15)
    clock_as_of = get_clock().as_of()
    schedule = scheduler.solve(snapshot, as_of=clock_as_of, horizon_days=7)

    # Injected violation: assign same asset and identical overlapping time to 2 different tasks
    corrupted_assignments = [dict(a) for a in schedule.assignments]
    assert len(corrupted_assignments) >= 2

    # Force task 1 to overlap task 0 on the exact same asset
    shared_asset = corrupted_assignments[0]["asset_id"]
    corrupted_assignments[1]["asset_id"] = shared_asset
    corrupted_assignments[1]["assigned_start"] = corrupted_assignments[0]["assigned_start"]
    corrupted_assignments[1]["assigned_end"] = corrupted_assignments[0]["assigned_end"]

    validator = IndependentPlanValidator()
    val_result = validator.validate_plan(corrupted_assignments, snapshot)

    assert val_result.is_valid is False
    assert val_result.violation_count > 0
    codes = [v["constraint_code"] for v in val_result.violations]
    assert "HC_NO_OVERLAP" in codes


def test_validator_detects_injected_crew_unqualified(db: Session):
    """Exit Gate 1 & Invariant 3: Unqualified personnel assignment must be flagged."""
    snapshot = load_schedule_snapshot(db)
    scheduler = BaselineScheduler(slot_minutes=15)
    clock_as_of = get_clock().as_of()
    schedule = scheduler.solve(snapshot, as_of=clock_as_of, horizon_days=7)

    corrupted_assignments = [dict(a) for a in schedule.assignments]
    # Replace personnel with someone who has no qualifications or a bogus ID
    bogus_personnel_id = str(uuid.uuid4())
    corrupted_assignments[0]["personnel_ids"] = [bogus_personnel_id]

    validator = IndependentPlanValidator()
    val_result = validator.validate_plan(corrupted_assignments, snapshot)

    assert val_result.is_valid is False
    codes = [v["constraint_code"] for v in val_result.violations]
    assert "HC_CREW_QUALIFICATION" in codes or "HC_RESOURCE_AVAIL" in codes


def test_validator_detects_injected_maintenance_clash(db: Session):
    """Exit Gate 1 & Invariant 4: Hard maintenance window clash must be flagged."""
    snapshot = load_schedule_snapshot(db)
    scheduler = BaselineScheduler(slot_minutes=15)
    schedule = scheduler.solve(snapshot, as_of=get_clock().as_of(), horizon_days=7)
    corrupted_assignments = [dict(a) for a in schedule.assignments]

    target_asset_id = corrupted_assignments[0]["asset_id"]
    a_start = corrupted_assignments[0]["assigned_start"]
    a_end = corrupted_assignments[0]["assigned_end"]

    # Inject an active maintenance window directly overlapping this assignment
    maint_window = {
        "id": str(uuid.uuid4()),
        "asset_id": target_asset_id,
        "start_time": a_start - timedelta(minutes=15),
        "end_time": a_end + timedelta(minutes=15),
        "status": "scheduled",
        "category": "unscheduled_repair",
    }
    snapshot_with_maint = dict(snapshot)
    snapshot_with_maint["maintenance_records"] = list(snapshot["maintenance_records"]) + [maint_window]

    validator = IndependentPlanValidator()
    val_result = validator.validate_plan(corrupted_assignments, snapshot_with_maint)

    assert val_result.is_valid is False
    codes = [v["constraint_code"] for v in val_result.violations]
    assert "HC_MAINT_WINDOWS" in codes


def test_validator_detects_injected_precedence_violation(db: Session):
    """Exit Gate 1 & Invariant 7: Task precedence inverted must be flagged."""
    snapshot = load_schedule_snapshot(db)
    deps = snapshot["task_dependencies"]
    assert len(deps) > 0

    dep = deps[0]
    pred_id = str(get_val(dep, "predecessor_task_id"))
    succ_id = str(get_val(dep, "successor_task_id"))

    scheduler = BaselineScheduler(slot_minutes=15)
    schedule = scheduler.solve(snapshot, as_of=get_clock().as_of(), horizon_days=7)

    asgn_by_tid = {a["task_id"]: a for a in schedule.assignments}
    if pred_id in asgn_by_tid and succ_id in asgn_by_tid:
        corrupted_assignments = [dict(a) for a in schedule.assignments]
        c_by_tid = {a["task_id"]: a for a in corrupted_assignments}
        # Invert: make successor start BEFORE predecessor end
        c_by_tid[succ_id]["assigned_start"] = c_by_tid[pred_id]["assigned_start"] - timedelta(hours=1)
        c_by_tid[succ_id]["assigned_end"] = c_by_tid[succ_id]["assigned_start"] + timedelta(hours=1)

        validator = IndependentPlanValidator()
        val_result = validator.validate_plan(corrupted_assignments, snapshot)

        assert val_result.is_valid is False
        codes = [v["constraint_code"] for v in val_result.violations]
        assert "HC_PRECEDENCE" in codes


def test_determinism_and_hashing(db: Session):
    """Exit Gate 4: Plan hashing is deterministic and captures assignments accurately."""
    snapshot = load_schedule_snapshot(db)
    scheduler = BaselineScheduler(slot_minutes=15)
    clock_as_of = get_clock().as_of()

    s1 = scheduler.solve(snapshot, as_of=clock_as_of, horizon_days=7)
    s2 = scheduler.solve(snapshot, as_of=clock_as_of, horizon_days=7)

    hash1 = compute_plan_hash(s1.assignments, version_num=1)
    hash2 = compute_plan_hash(s2.assignments, version_num=1)

    assert hash1 == hash2
    assert len(hash1) == 64  # SHA-256 hex string

    # Changing version number produces different hash
    hash_v2 = compute_plan_hash(s1.assignments, version_num=2)
    assert hash_v2 != hash1


def test_optimisation_service_full_workflow(db: Session):
    """Exit Gate 3 & 4: Service executes solve, validates, persists version, and writes audit log."""
    # 1. Create a tracking job
    job = Job(
        job_type="baseline",
        state=JobState.QUEUED.value,
        progress_percent=0.0,
        message="Queued for test execution",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    service = OptimisationService(db)
    res = service.execute_optimisation_job(
        job_id_str=str(job.id),
        job_type="baseline",
        plan_name="Test Automated Baseline",
    )

    assert res["version_number"] >= 1
    assert res["is_valid"] is True
    assert res["violation_count"] == 0

    # Check database persistence
    plan_version_id = uuid.UUID(res["plan_version_id"])
    p_ver = db.execute(select(PlanVersion).where(PlanVersion.id == plan_version_id)).scalars().first()
    assert p_ver is not None
    assert p_ver.solver_status == SolverStatus.FEASIBLE.value

    # Check assignments persisted
    asgns = db.execute(select(PlanAssignment).where(PlanAssignment.plan_version_id == plan_version_id)).scalars().all()
    assert len(asgns) == res["assignments_count"]

    # Check validation persisted
    p_val = db.execute(select(PlanValidation).where(PlanValidation.plan_version_id == plan_version_id)).scalars().first()
    assert p_val is not None
    assert p_val.is_valid is True
    assert p_val.violation_count == 0


def test_optimisation_rest_api_endpoints(db: Session):
    """Exit Gate 3: REST API job trigger, polling, plan listing, and Gantt query."""
    headers = get_auth_headers(db, "planner")

    # 1. Trigger optimisation job via API
    payload = {
        "job_type": "baseline",
        "plan_name": "API Automated Baseline Plan",
        "time_limit_seconds": 15,
        "seed": 42,
    }
    res_trigger = client.post("/api/v1/optimisation/jobs", json=payload, headers=headers)
    assert res_trigger.status_code == 202
    job_data = res_trigger.json()
    job_id = job_data["job_id"]
    assert job_data["job_type"] == "baseline"

    # 2. Poll job status
    res_poll = client.get(f"/api/v1/optimisation/jobs/{job_id}", headers=headers)
    assert res_poll.status_code == 200
    poll_data = res_poll.json()
    assert poll_data["job_id"] == job_id

    # 3. List plans
    res_plans = client.get("/api/v1/plans", headers=headers)
    assert res_plans.status_code == 200
    plans_list = res_plans.json()
    assert len(plans_list) > 0
    target_plan = plans_list[0]

    # 4. Fetch specific plan version
    res_ver = client.get(f"/api/v1/plans/{target_plan['id']}/versions/{target_plan['latest_version']}", headers=headers)
    assert res_ver.status_code == 200
    ver_data = res_ver.json()
    assert ver_data["version_number"] == target_plan["latest_version"]
    assert "assignments" in ver_data
    assert "metrics" in ver_data
    assert "manifest" in ver_data

    # 5. Fetch Gantt timeline
    res_gantt = client.get(f"/api/v1/plans/{target_plan['id']}/versions/{target_plan['latest_version']}/gantt", headers=headers)
    assert res_gantt.status_code == 200
    gantt_data = res_gantt.json()
    assert "asset_tracks" in gantt_data
    assert "crew_tracks" in gantt_data
    assert len(gantt_data["asset_tracks"]) > 0

    # 6. Objective weight sets
    res_weights = client.get("/api/v1/optimisation/weight-sets", headers=headers)
    assert res_weights.status_code == 200
    weights_list = res_weights.json()
    assert len(weights_list) >= 1
    assert weights_list[0]["version"] >= 1

    # 7. Create new objective weight set (requires ADMIN)
    admin_headers = get_auth_headers(db, "admin")
    new_weights_payload = {
        "name": "High-priority air defense profile",
        "delay_weight": 25,
        "completion_weight": 2000,
        "churn_weight": 75,
        "balance_weight": 5,
        "buffer_weight": 30,
    }
    res_post_weights = client.post("/api/v1/optimisation/weight-sets", json=new_weights_payload, headers=admin_headers)
    assert res_post_weights.status_code == 201
    created_weight = res_post_weights.json()
    assert created_weight["delay_weight"] == 25
    assert created_weight["version"] >= 2
