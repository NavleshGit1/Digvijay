"""Phase 6 Events, Disruption Recovery & Replanning Test Suite (Milestone M1).

Validates:
1. Alert rules evaluation, anti-flapping deduplication (15m sliding window), and acknowledgment/resolution.
2. Alert REST API endpoints: GET /alerts, GET /alerts/summary, POST /alerts/evaluate, acknowledge, resolve.
3. Operational Impact Detector: NetworkX multi-entity dependency graph traversal, DAG ripple detection, crew conflicts.
4. Maintenance Disruption Endpoints: GET /impact, POST /simulate-delay, PATCH /maintenance/records/{id}.
5. Constrained Replanning Engine: Frozen window enforcement, CP-SAT warm start hints, churn penalty minimization.
6. Strict Human-in-the-Loop Governance: Replan generates 'proposed' version only; never auto-approves.
7. Milestone M1 10-Step Operational Disruption Workflow end-to-end integration.
"""
from datetime import datetime, timedelta, timezone
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.clock import get_clock
from app.core.enums import JobState, PlanKind, PlanSource, PlanStatus, SolverStatus, UserRole
from app.core.security import create_access_token
from app.engines.optimisation.baseline import BaselineScheduler
from app.engines.replanning.impact import OperationalImpactDetector
from app.main import create_app
from app.models.alerts import Alert, AlertRule
from app.models.identity import Role, User
from app.models.jobs import Job
from app.models.operations import MaintenanceRecord, Task
from app.models.plans import ApprovalRecord, Plan, PlanAssignment, PlanValidation, PlanVersion
from app.models.resources import Asset
from app.services.alerts import (
    acknowledge_alert,
    evaluate_system_alerts,
    resolve_alert,
    seed_default_alert_rules,
)
from app.services.governance import GovernanceService
from app.services.optimisation import OptimisationService, compute_plan_hash, load_schedule_snapshot
from app.services.replanning import ReplanningService

app = create_app()
client = TestClient(app)


def get_auth_headers(db: Session, username_or_role: str) -> dict[str, str]:
    """Retrieves or creates user with target role and returns Bearer token authorization header."""
    user = db.execute(select(User).where(User.username == username_or_role)).scalars().first()
    if not user:
        user = db.execute(select(User).where(User.email.ilike(f"{username_or_role}%"))).scalars().first()
    if not user:
        role = db.execute(select(Role).where(Role.name == username_or_role)).scalars().first()
        if not role:
            role = Role(name=username_or_role, description=f"{username_or_role} role")
            db.add(role)
            db.flush()
        user = User(
            username=f"test_{username_or_role}_{uuid.uuid4().hex[:6]}",
            email=f"{username_or_role}_{uuid.uuid4().hex[:6]}@airops.test",
            hashed_password="test_hashed_password",
            roles=[role],
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    roles = [r.name for r in user.roles]
    token = create_access_token(subject=user.username, roles=roles)
    return {"Authorization": f"Bearer {token}"}


# -----------------------------------------------------------------------------
# Test 1: Alert Subsystem & Anti-Flapping Deduplication
# -----------------------------------------------------------------------------
def test_alert_rules_evaluation_and_anti_flapping(db: Session):
    """Verifies that alert rules evaluate correctly and deduplicate within the 15-minute sliding window."""
    seed_default_alert_rules(db)
    clock_as_of = get_clock().as_of()

    # Run evaluation round 1
    eval_res_1 = evaluate_system_alerts(db, as_of=clock_as_of)
    assert isinstance(eval_res_1, dict)
    assert "created" in eval_res_1

    # Fetch newly created alerts
    alerts_1 = db.execute(select(Alert).where(Alert.status == "new")).scalars().all()
    assert len(alerts_1) > 0, "Expected at least one operational alert to trigger on initial state"

    first_alert = alerts_1[0]
    initial_count = first_alert.count
    initial_dedup = first_alert.dedup_key
    assert initial_count >= 1
    assert len(initial_dedup) == 16

    # Run evaluation round 2 within the 15-minute sliding window (simulate same event continuing)
    eval_res_2 = evaluate_system_alerts(db, as_of=clock_as_of + timedelta(minutes=5))
    assert eval_res_2["updated"] >= 1, "Expected anti-flapping to increment existing alert count"

    db.refresh(first_alert)
    assert first_alert.count == initial_count + 1, "Anti-flapping must increment occurrence counter"

    # Test Acknowledge Alert
    ack_res = acknowledge_alert(db, first_alert.id, acknowledged_by="lead_reviewer")
    assert ack_res.status == "acknowledged"
    assert ack_res.acknowledged_by == "lead_reviewer"
    assert ack_res.acknowledged_at is not None

    # Test Resolve Alert
    res_alert = resolve_alert(
        db,
        first_alert.id,
        resolved_by="lead_reviewer",
        resolution_notes="Maintenance completed and certified airworthy",
    )
    assert res_alert.status == "resolved"
    assert res_alert.resolved_by == "lead_reviewer"


def test_alerts_api_endpoints(db: Session):
    """Verifies REST endpoints for listing, summarizing, acknowledging, and resolving alerts."""
    seed_default_alert_rules(db)
    evaluate_system_alerts(db)

    headers = get_auth_headers(db, "reviewer")

    # 1. GET /alerts
    res = client.get("/api/v1/alerts", headers=headers)
    assert res.status_code == 200
    alerts_data = res.json()
    assert isinstance(alerts_data, list)
    assert len(alerts_data) > 0

    target_alert_id = alerts_data[0]["id"]

    # 2. GET /alerts/summary
    summary_res = client.get("/api/v1/alerts/summary", headers=headers)
    assert summary_res.status_code == 200
    summary = summary_res.json()
    assert "total_active" in summary
    assert "critical_count" in summary
    assert summary["total_active"] >= 1

    # 3. POST /alerts/{id}/acknowledge
    ack_res = client.post(f"/api/v1/alerts/{target_alert_id}/acknowledge", headers=headers)
    assert ack_res.status_code == 200
    assert ack_res.json()["status"] == "acknowledged"

    # 4. POST /alerts/{id}/resolve
    res_res = client.post(
        f"/api/v1/alerts/{target_alert_id}/resolve",
        json={"resolution_notes": "Issue cleared via automated test"},
        headers=headers,
    )
    assert res_res.status_code == 200
    assert res_res.json()["status"] == "resolved"


# -----------------------------------------------------------------------------
# Test 2: NetworkX Graph Impact Detector & Maintenance Endpoints
# -----------------------------------------------------------------------------
def test_networkx_graph_impact_detector(db: Session):
    """Verifies multi-entity NetworkX DAG traversal detects directly affected and cascading tasks."""
    clock_as_of = get_clock().as_of()
    detector = OperationalImpactDetector(db, as_of=clock_as_of)

    # Find a maintenance record with an airframe
    maint = db.execute(select(MaintenanceRecord).limit(1)).scalars().first()
    assert maint is not None, "Expected seeded maintenance record"

    # Run impact detection with a +120m delay
    impact = detector.detect_maintenance_impact(maint.id, delay_minutes=120)
    assert impact.record_id == str(maint.id)
    assert impact.delay_minutes == 120
    assert isinstance(impact.plan_invalidated, bool)
    assert isinstance(impact.directly_affected_count, int)
    assert isinstance(impact.cascading_affected_count, int)
    assert isinstance(impact.affected_tasks, list)


def test_maintenance_delay_simulation_api(db: Session):
    """Verifies simulate-delay endpoint extends scheduled maintenance and flags impact."""
    maint = db.execute(select(MaintenanceRecord).limit(1)).scalars().first()
    assert maint is not None

    headers = get_auth_headers(db, "planner")

    # 1. GET impact preview (read-only)
    preview_res = client.get(
        f"/api/v1/maintenance/records/{maint.id}/impact?delay_minutes=60",
        headers=headers,
    )
    assert preview_res.status_code == 200
    preview_data = preview_res.json()
    assert preview_data["record_id"] == str(maint.id)
    assert preview_data["delay_minutes"] == 60

    # 2. POST simulate-delay (commits delay)
    sim_res = client.post(
        f"/api/v1/maintenance/records/{maint.id}/simulate-delay",
        json={
            "delay_minutes": 45,
            "reason": "Test hydraulic actuator inspection delay",
        },
        headers=headers,
    )
    assert sim_res.status_code == 200
    sim_data = sim_res.json()
    assert sim_data["delay_minutes"] == 45
    assert "extended_scheduled_end" in sim_data
    assert "impact" in sim_data


# -----------------------------------------------------------------------------
# Test 3: Constrained Replanning with Frozen Window & Churn Minimization
# -----------------------------------------------------------------------------
def test_constrained_replanning_engine(db: Session):
    """Verifies that ReplanningService creates a 'proposed' version preserving frozen commitments."""
    clock_as_of = get_clock().as_of()

    # Ensure an approved baseline plan exists
    opt_service = OptimisationService(db)
    baseline_job_id = str(uuid.uuid4())
    job = Job(id=uuid.UUID(baseline_job_id), job_type="optimisation_baseline", state=JobState.QUEUED.value)
    db.add(job)
    db.commit()

    unique_plan_name = f"Test Baseline For Replan {uuid.uuid4().hex[:6]}"
    base_res = opt_service.execute_optimisation_job(
        job_id_str=baseline_job_id,
        job_type="baseline",
        plan_name=unique_plan_name,
        time_limit_seconds=5.0,
        seed=42,
        as_of=clock_as_of,
    )

    plan_id = uuid.UUID(base_res["plan_id"])
    plan = db.get(Plan, plan_id)
    v1 = db.execute(
        select(PlanVersion).where(PlanVersion.plan_id == plan_id, PlanVersion.version_number == 1)
    ).scalars().first()

    # Reviewer approves version 1 so it becomes the current approved plan
    reviewer_user = db.execute(select(User)).scalars().first()
    gov_service = GovernanceService(db)
    gov_service.approve_plan_version(
        plan_id=plan_id,
        version_number=1,
        reviewer=reviewer_user,
        reason="Baseline approved for replanning test",
    )
    db.refresh(plan)
    assert plan.current_approved_version_id == v1.id

    # Execute Replan with 120m frozen window
    replan_job_id = str(uuid.uuid4())
    r_job = Job(id=uuid.UUID(replan_job_id), job_type="optimisation_replan", state=JobState.QUEUED.value)
    db.add(r_job)
    db.commit()

    replan_service = ReplanningService(db)
    replan_res = replan_service.execute_replan(
        job_id_str=replan_job_id,
        plan_id=plan_id,
        frozen_window_minutes=120,
        disruption_reason="Test disruption overrun",
        time_limit_seconds=10.0,
        seed=42,
        as_of=clock_as_of,
    )

    assert replan_res["kind"] == "replan"
    assert replan_res["version_number"] == 2
    # CRITICAL INVARIANT: Replan must be PROPOSED (never auto-approved)
    assert replan_res["status"] == PlanStatus.PROPOSED.value

    # Verify churn metrics
    assert "churn" in replan_res
    churn = replan_res["churn"]
    assert "tasks_shifted" in churn
    assert "total_shift_minutes" in churn
    assert "assets_reassigned" in churn
    assert "frozen_tasks_preserved" in churn
    assert "churn_index" in churn

    # Verify Plan record in DB: Current approved version must STILL be v1
    db.refresh(plan)
    assert plan.current_approved_version_id == v1.id, "Replan proposal MUST NOT auto-approve or overwrite approved plan!"


# -----------------------------------------------------------------------------
# Test 4: Milestone M1 Complete 10-Step Operational Disruption Workflow
# -----------------------------------------------------------------------------
def test_milestone_m1_ten_step_end_to_end_flow(db: Session):
    """Executes the complete 10-step M1 operational disruption flow.
    
    1. Load seeded dataset
    2. Generate baseline
    3. Reviewer approves baseline
    4. Inject maintenance delay disruption
    5. NetworkX graph impact detector identifies affected downstream tasks
    6. Run replanning with frozen window and churn objective
    7. Compare diff (assignments shifted, delay delta)
    8. Reviewer reviews proposal and approves
    9. Previous plan superseded, current approved updated
    10. Immutable audit trail captures entire decision history
    """
    clock_as_of = get_clock().as_of()
    headers_planner = get_auth_headers(db, "planner")
    headers_reviewer = get_auth_headers(db, "reviewer")

    # Step 1: Snapshot / dataset verified
    snapshot = load_schedule_snapshot(db)
    assert len(snapshot["tasks"]) > 0
    assert len(snapshot["assets"]) > 0

    # Step 2: Generate baseline
    plan_name = f"M1 Master Plan {uuid.uuid4().hex[:6]}"
    res_b = client.post(
        "/api/v1/optimisation/jobs",
        json={
            "job_type": "baseline",
            "plan_name": plan_name,
            "time_limit_seconds": 5.0,
            "seed": 42,
            "run_async": False,
        },
        headers=headers_planner,
    )
    assert res_b.status_code in [200, 202]
    plan_id = res_b.json()["result"]["plan_id"]
    etag_v1 = f'"{res_b.json()["result"]["snapshot_hash"]}"'

    # Step 3: Reviewer approves baseline
    res_app1 = client.post(
        f"/api/v1/plans/{plan_id}/versions/1/approve",
        headers={**headers_reviewer, "If-Match": etag_v1},
        json={"reason": "Step 3: Reviewer approves baseline master schedule"},
    )
    assert res_app1.status_code == 200
    assert res_app1.json()["current_approved_version"] == 1

    # Step 4: Inject maintenance delay disruption
    maint = db.execute(select(MaintenanceRecord).limit(1)).scalars().first()
    assert maint is not None
    res_delay = client.post(
        f"/api/v1/maintenance/records/{maint.id}/simulate-delay",
        json={
            "delay_minutes": 90,
            "reason": "Step 4: Mechanical turbine crack detected during scheduled inspection",
        },
        headers=headers_planner,
    )
    assert res_delay.status_code == 200
    delay_data = res_delay.json()
    assert delay_data["delay_minutes"] == 90

    # Step 5: NetworkX graph impact detector identifies affected downstream tasks
    res_impact = client.get(
        f"/api/v1/maintenance/records/{maint.id}/impact?delay_minutes=90",
        headers=headers_planner,
    )
    assert res_impact.status_code == 200
    impact = res_impact.json()
    assert "directly_affected_count" in impact
    assert "cascading_affected_count" in impact

    # Step 6: Run replanning with frozen window and churn objective
    res_replan = client.post(
        "/api/v1/optimisation/replan",
        json={
            "plan_id": plan_id,
            "frozen_window_minutes": 120,
            "disruption_reason": "Step 6: Turbine crack recovery replan",
            "time_limit_seconds": 10.0,
            "seed": 42,
            "run_async": False,
        },
        headers=headers_planner,
    )
    assert res_replan.status_code in [200, 202]
    replan_proposal = res_replan.json()["result"]
    assert replan_proposal["version_number"] == 2
    assert replan_proposal["kind"] == "replan"
    assert replan_proposal["status"] == "proposed"
    assert "churn" in replan_proposal
    etag_v2 = f'"{replan_proposal["snapshot_hash"]}"'

    # Step 7: Compare diff (assignments shifted, delay delta)
    res_diff = client.get(
        f"/api/v1/plans/{plan_id}/diff?target_version=2&baseline_version=1",
        headers=headers_reviewer,
    )
    assert res_diff.status_code == 200
    diff_data = res_diff.json()
    assert diff_data["target_version"] == 2
    assert diff_data["baseline_version"] == 1
    assert "shifted_assignments" in diff_data
    assert "metric_deltas" in diff_data

    # Step 8: Reviewer reviews proposal and approves
    res_app2 = client.post(
        f"/api/v1/plans/{plan_id}/versions/2/approve",
        headers={**headers_reviewer, "If-Match": etag_v2},
        json={"reason": "Step 8: Reviewer accepts proposal with minimized churn and preserved frozen commitments"},
    )
    assert res_app2.status_code == 200

    # Step 9: Previous plan superseded, current approved updated
    plan_obj = db.get(Plan, uuid.UUID(plan_id))
    db.refresh(plan_obj)
    v1_obj = db.execute(
        select(PlanVersion).where(PlanVersion.plan_id == plan_obj.id, PlanVersion.version_number == 1)
    ).scalars().first()
    v2_obj = db.execute(
        select(PlanVersion).where(PlanVersion.plan_id == plan_obj.id, PlanVersion.version_number == 2)
    ).scalars().first()

    assert v1_obj.status == PlanStatus.SUPERSEDED.value, "Version 1 must be superseded"
    assert v2_obj.status == PlanStatus.APPROVED.value, "Version 2 must be approved"
    assert plan_obj.current_approved_version_id == v2_obj.id, "Plan current approved version must be v2"

    # Step 10: Immutable audit trail captures entire decision history
    records_res = client.get(
        f"/api/v1/plans/{plan_id}/approval-records",
        headers=headers_reviewer,
    )
    assert records_res.status_code == 200
    app_records = records_res.json()
    assert len(app_records) >= 2, "Expected at least 2 approval records (v1 and v2)"
    v2_record = next(r for r in app_records if r["plan_version_number"] == 2)
    assert v2_record["decision"] == "approved"
    assert "minimized churn" in v2_record["reason"]
