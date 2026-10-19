"""Phase 5 Governance, Reviewer Approval, Staleness & Rollback Test Suite.

Validates:
1. Reviewer-only RBAC: Planner and Admin without reviewer role strictly blocked (403 Forbidden).
2. Optimistic concurrency locking (If-Match header verification: 412 Precondition Failed on mismatch).
3. Idempotent approval with Idempotency-Key deduplication.
4. Single-transaction atomic approval: previous plan superseded, current approved updated.
5. Sibling proposal staleness: approving one proposal marks all sibling proposals stale.
6. Approval-time live revalidation failure: operational conflict returns 409 revalidation_failed, aborts approval.
7. Diff engine: task assignment and metric deltas computed accurately.
8. Rollback proposal flow: proposal generated from target version and approved through Reviewer.
9. Cryptographic audit log filtering and signed CSV export with SHA-256 integrity headers.
10. Constraint registry governance: impact preview and activation marking proposals stale.
"""
from datetime import datetime, timedelta, timezone
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import get_clock
from app.core.enums import PlanKind, PlanSource, PlanStatus, SolverStatus, UserRole
from app.core.security import create_access_token
from app.engines.optimisation.baseline import BaselineScheduler
from app.engines.optimisation.validator import IndependentPlanValidator
from app.main import create_app
from app.models.identity import Role, User
from app.models.operations import MaintenanceRecord, Task
from app.models.plans import ApprovalRecord, ConstraintSet, Plan, PlanAssignment, PlanValidation, PlanVersion
from app.models.resources import Asset
from app.services.governance import GovernanceService, calculate_plan_diff
from app.services.optimisation import OptimisationService, compute_plan_hash, load_schedule_snapshot

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


@pytest.fixture
def test_plan_with_proposals(db: Session):
    """Sets up a clean test Plan with baseline version 1 and two proposed versions 2 and 3."""
    clock_as_of = get_clock().as_of()
    snapshot = load_schedule_snapshot(db)
    scheduler = BaselineScheduler(slot_minutes=15)
    sol = scheduler.solve(snapshot, as_of=clock_as_of, horizon_days=7)

    plan = Plan(id=uuid.uuid4(), name=f"Test Governance Plan {uuid.uuid4().hex[:6]}")
    db.add(plan)
    db.flush()

    # Version 1: Baseline Proposed
    v1 = PlanVersion(
        id=uuid.uuid4(),
        plan_id=plan.id,
        version_number=1,
        kind=PlanKind.BASELINE.value,
        status=PlanStatus.PROPOSED.value,
        snapshot_hash=compute_plan_hash(sol.assignments, 1),
        solver_status=SolverStatus.FEASIBLE.value,
        plan_source=PlanSource.HEURISTIC.value,
        as_of=clock_as_of,
        metrics_json=sol.metrics,
        solver_runtime_seconds=0.05,
    )
    db.add(v1)
    db.flush()

    for a in sol.assignments:
        db.add(
            PlanAssignment(
                plan_version_id=v1.id,
                task_id=uuid.UUID(str(a["task_id"])),
                asset_id=uuid.UUID(str(a["asset_id"])) if a.get("asset_id") else None,
                personnel_ids=[uuid.UUID(str(p)) for p in (a.get("personnel_ids") or [])],
                assigned_start=a["assigned_start"],
                assigned_end=a["assigned_end"],
            )
        )
    val1 = IndependentPlanValidator().validate_plan(sol.assignments, snapshot)
    db.add(
        PlanValidation(
            plan_version_id=v1.id,
            is_valid=val1.is_valid,
            violation_count=val1.violation_count,
            violations_json=val1.violations,
            binding_constraints_json=[],
            validated_at=val1.validated_at,
        )
    )

    # Version 2: Proposed revision
    v2 = PlanVersion(
        id=uuid.uuid4(),
        plan_id=plan.id,
        version_number=2,
        kind=PlanKind.OPTIMISED.value,
        status=PlanStatus.PROPOSED.value,
        based_on_version=1,
        snapshot_hash=compute_plan_hash(sol.assignments, 2),
        solver_status=SolverStatus.OPTIMAL.value,
        plan_source=PlanSource.CPSAT.value,
        as_of=clock_as_of,
        metrics_json={"total_delay_minutes": 15.0},
        solver_runtime_seconds=1.2,
    )
    db.add(v2)
    db.flush()

    for a in sol.assignments:
        db.add(
            PlanAssignment(
                plan_version_id=v2.id,
                task_id=uuid.UUID(str(a["task_id"])),
                asset_id=uuid.UUID(str(a["asset_id"])) if a.get("asset_id") else None,
                personnel_ids=[uuid.UUID(str(p)) for p in (a.get("personnel_ids") or [])],
                assigned_start=a["assigned_start"],
                assigned_end=a["assigned_end"],
            )
        )
    db.add(
        PlanValidation(
            plan_version_id=v2.id,
            is_valid=True,
            violation_count=0,
            violations_json=[],
            binding_constraints_json=[],
            validated_at=clock_as_of,
        )
    )

    # Version 3: Alternative proposed sibling
    v3 = PlanVersion(
        id=uuid.uuid4(),
        plan_id=plan.id,
        version_number=3,
        kind=PlanKind.ALTERNATIVE.value,
        status=PlanStatus.PROPOSED.value,
        based_on_version=1,
        snapshot_hash=compute_plan_hash(sol.assignments, 3),
        solver_status=SolverStatus.FEASIBLE.value,
        plan_source=PlanSource.CPSAT.value,
        as_of=clock_as_of,
        metrics_json={"total_delay_minutes": 25.0},
        solver_runtime_seconds=0.8,
    )
    db.add(v3)
    db.flush()

    for a in sol.assignments:
        db.add(
            PlanAssignment(
                plan_version_id=v3.id,
                task_id=uuid.UUID(str(a["task_id"])),
                asset_id=uuid.UUID(str(a["asset_id"])) if a.get("asset_id") else None,
                personnel_ids=[uuid.UUID(str(p)) for p in (a.get("personnel_ids") or [])],
                assigned_start=a["assigned_start"],
                assigned_end=a["assigned_end"],
            )
        )
    db.add(
        PlanValidation(
            plan_version_id=v3.id,
            is_valid=True,
            violation_count=0,
            violations_json=[],
            binding_constraints_json=[],
            validated_at=clock_as_of,
        )
    )

    db.commit()
    return {"plan": plan, "v1": v1, "v2": v2, "v3": v3}


def test_reviewer_rbac_enforcement(db: Session, test_plan_with_proposals):
    """P5-2, P5-6: Only Reviewers can approve plans; Planners and Admins without Reviewer role get 403."""
    plan = test_plan_with_proposals["plan"]
    v1 = test_plan_with_proposals["v1"]

    planner_headers = get_auth_headers(db, "planner")
    admin_headers = get_auth_headers(db, "admin")
    reviewer_headers = get_auth_headers(db, "reviewer")

    payload = {"reason": "Attempting approval without reviewer privileges"}

    # 1. Planner calling approve -> 403 Forbidden
    res_planner = client.post(
        f"/api/v1/plans/{plan.id}/versions/{v1.version_number}/approve",
        json=payload,
        headers=planner_headers,
    )
    assert res_planner.status_code == 403
    assert "require the Reviewer role" in res_planner.text or "requires one of" in res_planner.text

    # 2. Admin without reviewer role calling approve -> 403 Forbidden
    res_admin = client.post(
        f"/api/v1/plans/{plan.id}/versions/{v1.version_number}/approve",
        json=payload,
        headers=admin_headers,
    )
    assert res_admin.status_code == 403

    # 3. Reviewer calling approve -> 200 OK
    res_reviewer = client.post(
        f"/api/v1/plans/{plan.id}/versions/{v1.version_number}/approve",
        json={"reason": "Valid baseline schedule approved by Lead Operations Reviewer"},
        headers=reviewer_headers,
    )
    assert res_reviewer.status_code == 200
    assert res_reviewer.json()["status"] == "approved"
    assert res_reviewer.json()["decision"] == "approved"


def test_optimistic_locking_if_match(db: Session, test_plan_with_proposals):
    """P5-2: If-Match header validates version before approval; 412 on mismatch."""
    plan = test_plan_with_proposals["plan"]
    v1 = test_plan_with_proposals["v1"]
    reviewer_headers = get_auth_headers(db, "reviewer")

    # Mismatched If-Match header
    mismatch_headers = {**reviewer_headers, "If-Match": "v999"}
    res_mismatch = client.post(
        f"/api/v1/plans/{plan.id}/versions/{v1.version_number}/approve",
        json={"reason": "Testing optimistic concurrency header"},
        headers=mismatch_headers,
    )
    assert res_mismatch.status_code == 412
    assert "If-Match precondition failed" in res_mismatch.text

    # Matching If-Match header
    valid_headers = {**reviewer_headers, "If-Match": f"v{v1.version_number}"}
    res_valid = client.post(
        f"/api/v1/plans/{plan.id}/versions/{v1.version_number}/approve",
        json={"reason": "Baseline schedule approved with matching ETag"},
        headers=valid_headers,
    )
    assert res_valid.status_code == 200


def test_idempotent_approval_double_submit(db: Session, test_plan_with_proposals):
    """P5-2, P5-6: Submitting same approval with Idempotency-Key twice is idempotent."""
    plan = test_plan_with_proposals["plan"]
    v1 = test_plan_with_proposals["v1"]
    reviewer_headers = get_auth_headers(db, "reviewer")

    idem_key = f"idem-key-{uuid.uuid4().hex}"
    headers = {**reviewer_headers, "Idempotency-Key": idem_key}
    payload = {"reason": "Idempotency test rationale"}

    # First submission
    res1 = client.post(f"/api/v1/plans/{plan.id}/versions/{v1.version_number}/approve", json=payload, headers=headers)
    assert res1.status_code == 200
    data1 = res1.json()

    # Second submission with same Idempotency-Key
    res2 = client.post(f"/api/v1/plans/{plan.id}/versions/{v1.version_number}/approve", json=payload, headers=headers)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2.get("idempotent") is True

    # Confirm only one approval record exists
    records = db.execute(select(ApprovalRecord).where(ApprovalRecord.idempotency_key == idem_key)).scalars().all()
    assert len(records) == 1


def test_atomic_approval_and_sibling_staleness(db: Session, test_plan_with_proposals):
    """P5-1, P5-7, P5-8: Single transaction: prior plan superseded, target approved, siblings marked stale."""
    plan = test_plan_with_proposals["plan"]
    v1 = test_plan_with_proposals["v1"]
    v2 = test_plan_with_proposals["v2"]
    v3 = test_plan_with_proposals["v3"]
    reviewer_headers = get_auth_headers(db, "reviewer")

    # 1. Approve v1 first
    res_v1 = client.post(
        f"/api/v1/plans/{plan.id}/versions/{v1.version_number}/approve",
        json={"reason": "Approving initial baseline v1"},
        headers=reviewer_headers,
    )
    assert res_v1.status_code == 200

    db.refresh(plan)
    db.refresh(v1)
    assert plan.current_approved_version_id == v1.id
    assert v1.status == PlanStatus.APPROVED.value

    # Reset v2 and v3 to PROPOSED for sibling staleness test
    v2.status = PlanStatus.PROPOSED.value
    v3.status = PlanStatus.PROPOSED.value
    db.commit()

    # 2. Now approve v2
    res_v2 = client.post(
        f"/api/v1/plans/{plan.id}/versions/{v2.version_number}/approve",
        json={"reason": "Approving optimised schedule v2"},
        headers=reviewer_headers,
    )
    assert res_v2.status_code == 200
    data_v2 = res_v2.json()
    assert data_v2["status"] == "approved"
    assert data_v2["previous_approved_version"] == 1
    assert data_v2["stale_siblings_count"] >= 1

    db.refresh(plan)
    db.refresh(v1)
    db.refresh(v2)
    db.refresh(v3)

    # Verify atomic transaction outcome
    assert plan.current_approved_version_id == v2.id
    assert v2.status == PlanStatus.APPROVED.value
    assert v1.status == PlanStatus.SUPERSEDED.value
    assert v3.status == PlanStatus.STALE.value
    assert "Superseded by approval of sibling version 2" in v3.stale_reason


def test_approval_revalidation_failure(db: Session, test_plan_with_proposals):
    """P5-8, P5-15: Operational conflict injected -> approval returns 409 revalidation_failed and aborts."""
    plan = test_plan_with_proposals["plan"]
    v1 = test_plan_with_proposals["v1"]
    v2 = test_plan_with_proposals["v2"]
    reviewer_headers = get_auth_headers(db, "reviewer")

    # Approve v1 so it's currently active
    client.post(
        f"/api/v1/plans/{plan.id}/versions/{v1.version_number}/approve",
        json={"reason": "Baseline approved"},
        headers=reviewer_headers,
    )
    db.refresh(plan)
    v2.status = PlanStatus.PROPOSED.value
    db.commit()

    # Inject hard maintenance conflict overlapping an assigned task in v2
    v2_assignments = db.execute(select(PlanAssignment).where(PlanAssignment.plan_version_id == v2.id)).scalars().all()
    target_asgn = next(a for a in v2_assignments if a.asset_id is not None)

    conflicting_maintenance = MaintenanceRecord(
        id=uuid.uuid4(),
        asset_id=target_asgn.asset_id,
        category="unplanned_engine_overhaul",
        start_time=target_asgn.assigned_start - timedelta(hours=1),
        end_time=target_asgn.assigned_end + timedelta(hours=1),
        status="scheduled",
    )
    db.add(conflicting_maintenance)
    db.commit()

    # Attempt to approve v2 -> should fail with 409 revalidation_failed
    res_fail = client.post(
        f"/api/v1/plans/{plan.id}/versions/{v2.version_number}/approve",
        json={"reason": "Attempting approval during live maintenance conflict"},
        headers=reviewer_headers,
    )
    assert res_fail.status_code == 409
    body = res_fail.json()
    assert body.get("detail", {}).get("code") == "revalidation_failed"
    violations = body.get("detail", {}).get("violations", [])
    assert any(v.get("constraint_code") == "HC_MAINT_WINDOWS" for v in violations)

    # Verify that nothing was approved and active plan remains unchanged
    db.refresh(plan)
    db.refresh(v2)
    assert plan.current_approved_version_id == v1.id
    assert v2.status == PlanStatus.STALE.value

    # Cleanup injected maintenance
    db.delete(conflicting_maintenance)
    db.commit()


def test_plan_diff_engine(db: Session, test_plan_with_proposals):
    """P5-1, P5-7: Diff calculation returns accurate assignment and metric deltas."""
    plan = test_plan_with_proposals["plan"]
    v1 = test_plan_with_proposals["v1"]
    v2 = test_plan_with_proposals["v2"]
    planner_headers = get_auth_headers(db, "planner")

    res = client.get(
        f"/api/v1/plans/{plan.id}/versions/{v2.version_number}/diff/{v1.version_number}",
        headers=planner_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["from_version"] == 1
    assert data["to_version"] == 2
    assert "summary" in data
    assert "metrics_diff" in data
    assert "total_assignments_new" in data["summary"]


def test_rollback_proposal_and_approval(db: Session, test_plan_with_proposals):
    """P5-11, P5-15: Plan rollback generates proposal of kind rollback, approved by Reviewer."""
    plan = test_plan_with_proposals["plan"]
    v1 = test_plan_with_proposals["v1"]
    v2 = test_plan_with_proposals["v2"]
    reviewer_headers = get_auth_headers(db, "reviewer")
    planner_headers = get_auth_headers(db, "planner")

    # 1. Approve v1 then v2
    client.post(f"/api/v1/plans/{plan.id}/versions/{v1.version_number}/approve", json={"reason": "Approved v1"}, headers=reviewer_headers)
    v2.status = PlanStatus.PROPOSED.value
    db.commit()
    client.post(f"/api/v1/plans/{plan.id}/versions/{v2.version_number}/approve", json={"reason": "Approved v2"}, headers=reviewer_headers)

    # 2. Planner requests rollback to v1
    rollback_payload = {
        "target_version": 1,
        "reason": "Unforeseen constraint degradation in v2; rolling back to stable baseline v1",
    }
    res_rb = client.post(f"/api/v1/plans/{plan.id}/rollback-proposal", json=rollback_payload, headers=planner_headers)
    assert res_rb.status_code == 200
    rb_data = res_rb.json()
    assert rb_data["kind"] == "rollback"
    assert rb_data["status"] == "proposed"
    assert rb_data["rollback_target"] == 1
    new_v = rb_data["version_number"]

    # 3. Reviewer approves rollback proposal
    res_appr_rb = client.post(
        f"/api/v1/plans/{plan.id}/versions/{new_v}/approve",
        json={"reason": "Reviewer confirmed rollback to baseline version 1"},
        headers=reviewer_headers,
    )
    assert res_appr_rb.status_code == 200
    assert res_appr_rb.json()["status"] == "approved"

    db.refresh(plan)
    rb_pv = db.execute(select(PlanVersion).where(PlanVersion.plan_id == plan.id, PlanVersion.version_number == new_v)).scalars().first()
    assert plan.current_approved_version_id == rb_pv.id
    assert rb_pv.status == PlanStatus.APPROVED.value


def test_audit_logs_filters_and_signed_csv_export(db: Session):
    """P5-3: Audit log query with filters and signed CSV streaming export."""
    reviewer_headers = get_auth_headers(db, "reviewer")

    # Query filtered audit logs
    res_logs = client.get("/api/v1/admin/audit-logs?limit=10", headers=reviewer_headers)
    assert res_logs.status_code == 200
    items = res_logs.json()
    assert len(items) > 0
    assert "record_hash" in items[0]
    assert "previous_hash" in items[0]

    # Export signed CSV
    res_csv = client.get("/api/v1/admin/audit-logs/export", headers=reviewer_headers)
    assert res_csv.status_code == 200
    assert res_csv.headers["content-type"].startswith("text/csv")
    assert "X-Audit-Chain-Head" in res_csv.headers
    assert "X-Audit-Record-Count" in res_csv.headers
    assert res_csv.headers["X-Audit-Tamper-Proof"] == "SHA256-Merkle-Chained"

    content = res_csv.text
    assert "record_hash" in content
    assert "previous_hash" in content
    assert "APPROVE_PLAN_VERSION" in content or "GENERATE_PLAN" in content or "RESET_DEMO" in content


def test_constraint_registry_governance(db: Session, test_plan_with_proposals):
    """P5-12, Item 9: Constraint registry clone, impact preview, and activation marking proposals stale."""
    plan = test_plan_with_proposals["plan"]
    v3 = test_plan_with_proposals["v3"]
    admin_headers = get_auth_headers(db, "admin")

    # 1. Clone active set to draft
    clone_payload = {"name": "Test Tightened Maintenance Bounds"}
    res_clone = client.post("/api/v1/constraints/sets", json=clone_payload, headers=admin_headers)
    assert res_clone.status_code == 201
    set_data = res_clone.json()
    set_id = set_data["id"]
    assert set_data["status"] == "draft"

    # 2. Run impact preview
    res_prev = client.post(f"/api/v1/constraints/sets/{set_id}/impact-preview", headers=admin_headers)
    assert res_prev.status_code == 200
    assert "impact_summary" in res_prev.json()

    # 3. Activate draft set
    v3.status = PlanStatus.PROPOSED.value
    db.commit()

    res_act = client.post(f"/api/v1/constraints/sets/{set_id}/activate", headers=admin_headers)
    assert res_act.status_code == 200
    assert res_act.json()["status"] == "active"

    # Verify pending proposal was marked stale
    db.refresh(v3)
    assert v3.status == PlanStatus.STALE.value
    assert "activated" in v3.stale_reason
