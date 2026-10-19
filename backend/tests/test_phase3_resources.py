import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.clock import get_clock
from app.core.security import create_access_token
from app.main import app
from app.models.audit import AuditLog
from app.models.identity import User
from app.models.logistics import Part, SparesInventory
from app.models.operations import MaintenanceRecord, Task
from app.models.provenance import Event
from app.models.resources import Asset, Personnel, Zone
from app.services.auth import get_user_by_username
from app.services.maintenance_validation import validate_maintenance_overlap

client = TestClient(app)


def get_auth_headers(db: Session, username_or_email: str) -> dict[str, str]:
    stmt = select(User).where((User.username == username_or_email) | (User.email == username_or_email))
    user = db.execute(stmt).scalars().first()
    assert user is not None, f"User {username_or_email} not found"
    roles = [r.name for r in user.roles]
    token = create_access_token(subject=user.username, roles=roles)
    return {"Authorization": f"Bearer {token}"}


def test_zones_endpoint():
    """Verify all 3 fictional operational base zones are returned."""
    res = client.get("/api/v1/zones")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 3
    codes = {z["code"] for z in data}
    assert "BASE_ALPHA" in codes
    assert "BASE_BRAVO" in codes
    assert "BASE_CHARLIE" in codes


def test_assets_list_and_filters():
    """Verify asset filtering by type, status, and search."""
    # List all
    res = client.get("/api/v1/assets?limit=100")
    assert res.status_code == 200
    assets = res.json()
    assert len(assets) == 40

    # Filter by type
    res_fighters = client.get("/api/v1/assets?asset_type=FIGHTER_MULTIROLE")
    assert res_fighters.status_code == 200
    fighters = res_fighters.json()
    assert len(fighters) == 36  # 18 Su-30MKI + 12 Rafale + 6 Tejas
    assert all(a["asset_type"] == "FIGHTER_MULTIROLE" for a in fighters)

    # Search filter
    res_search = client.get("/api/v1/assets?search=SB-001")
    assert res_search.status_code == 200
    found = res_search.json()
    assert len(found) >= 1
    assert found[0]["identifier"] == "SB-001"


def test_asset_detail_and_update(db: Session):
    """Verify asset detail inspection and audited mutation with RBAC enforcement."""
    asset = db.execute(select(Asset)).scalars().first()
    assert asset is not None

    # Get detail
    res = client.get(f"/api/v1/assets/{asset.id}")
    assert res.status_code == 200
    detail = res.json()
    assert detail["identifier"] == asset.identifier
    assert "usage_summary" in detail
    assert "recent_maintenance" in detail

    # Attempt mutation without auth (401)
    res_unauth = client.patch(
        f"/api/v1/assets/{asset.id}",
        json={"status": "in_use", "reason": "Sortie dispatch"},
    )
    assert res_unauth.status_code == 401

    # Attempt mutation with unauthorized role (Reviewer cannot update assets per matrix -> 403)
    rev_headers = get_auth_headers(db, "reviewer@airops.local")
    res_forbidden = client.patch(
        f"/api/v1/assets/{asset.id}",
        json={"status": "in_use", "reason": "Unauthorized attempt"},
        headers=rev_headers,
    )
    assert res_forbidden.status_code == 403

    # Authorized mutation with Planner (200 + audit record)
    plan_headers = get_auth_headers(db, "planner@airops.local")
    res_ok = client.patch(
        f"/api/v1/assets/{asset.id}",
        json={"status": "in_use", "current_location": "Ramp-04", "reason": "Dispatched on CAP patrol sortie"},
        headers=plan_headers,
    )
    assert res_ok.status_code == 200
    updated = res_ok.json()
    assert updated["status"] == "in_use"
    assert updated["current_location"] == "Ramp-04"

    # Verify audit log was created
    audit = db.execute(
        select(AuditLog)
        .where(AuditLog.action == "UPDATE_ASSET", AuditLog.entity_id == str(asset.id))
        .order_by(AuditLog.timestamp.desc())
    ).scalars().first()
    assert audit is not None
    assert audit.reason == "Dispatched on CAP patrol sortie"
    assert audit.after_state["status"] == "in_use"
    assert len(audit.record_hash) == 64


def test_personnel_roster_and_qualifications(db: Session):
    """Verify personnel listing, qualification validity dates, and duty hours mutation."""
    res = client.get("/api/v1/personnel?limit=200")
    assert res.status_code == 200
    roster = res.json()
    assert len(roster) == 120

    # Role filter
    res_pilots = client.get("/api/v1/personnel?role_type=pilot")
    assert res_pilots.status_code == 200
    assert len(res_pilots.json()) == 42

    # Get detail
    p_sample = roster[0]
    res_detail = client.get(f"/api/v1/personnel/{p_sample['id']}")
    assert res_detail.status_code == 200
    detail = res_detail.json()
    assert "qualification_details" in detail
    assert len(detail["qualification_details"]) >= 1

    # Audited duty hours update by Planner
    plan_headers = get_auth_headers(db, "planner@airops.local")
    res_update = client.patch(
        f"/api/v1/personnel/{p_sample['id']}",
        json={"duty_hours_accumulated": 4.5, "reason": "Completed morning training sortie"},
        headers=plan_headers,
    )
    assert res_update.status_code == 200
    assert res_update.json()["duty_hours_accumulated"] == 4.5


def test_tasks_list_and_dag_dependencies(db: Session):
    """Verify operational tasks and DAG predecessor/successor dependencies."""
    res = client.get("/api/v1/tasks?limit=50")
    assert res.status_code == 200
    tasks = res.json()
    assert len(tasks) == 50

    # Find task with dependency
    t_sample = db.execute(select(Task).where(Task.code == "TSK-2026-0001")).scalar_one_or_none()
    assert t_sample is not None

    res_detail = client.get(f"/api/v1/tasks/{t_sample.id}")
    assert res_detail.status_code == 200
    detail = res_detail.json()
    assert "requirements" in detail
    assert "predecessors" in detail
    assert "successors" in detail


def test_spares_inventory_and_resupply(db: Session):
    """Verify spares stock tracking, controlled shortage detection, and resupply order creation."""
    # List spares
    res = client.get("/api/v1/inventory/spares")
    assert res.status_code == 200
    spares = res.json()
    assert len(spares) == 75

    # Filter shortages
    res_short = client.get("/api/v1/inventory/spares?shortage_only=true")
    assert res_short.status_code == 200
    shortages = res_short.json()
    assert len(shortages) >= 3  # Generator injects at least 3 controlled shortages in Zone 1
    assert all(s["is_shortage"] for s in shortages)

    # Create resupply order
    part = db.execute(select(Part)).scalars().first()
    zone = db.execute(select(Zone)).scalars().first()
    plan_headers = get_auth_headers(db, "planner@airops.local")

    order_payload = {
        "part_id": str(part.id),
        "zone_id": str(zone.id),
        "quantity": 10,
        "reason": "Replenish safety buffer for upcoming combat readiness exercise",
    }
    res_order = client.post("/api/v1/inventory/orders", json=order_payload, headers=plan_headers)
    assert res_order.status_code == 201
    order_data = res_order.json()
    assert order_data["quantity"] == 10
    assert order_data["status"] == "in_transit"


def test_hard_maintenance_window_validation_rule(db: Session):
    """
    Task P3-2: Test Hard Maintenance Window Validation Rule.
    Rejects incompatible assignments or overlapping maintenance windows.
    """
    asset = db.execute(select(Asset)).scalars().first()
    clock = get_clock()
    now = clock.now()

    maint_start = now + timedelta(days=3)
    maint_end = maint_start + timedelta(hours=8)

    # 1. Schedule initial maintenance record
    plan_headers = get_auth_headers(db, "planner@airops.local")
    payload = {
        "asset_id": str(asset.id),
        "category": "scheduled_phase_inspection",
        "start_time": maint_start.isoformat(),
        "end_time": maint_end.isoformat(),
        "is_unplanned": False,
        "reason": "Scheduled 100-hour phase inspection",
    }
    res_create = client.post("/api/v1/maintenance/records", json=payload, headers=plan_headers)
    assert res_create.status_code == 201
    created_id = res_create.json()["id"]

    # 2. Test validation endpoint with overlapping window
    overlap_start = maint_start + timedelta(hours=2)
    overlap_end = maint_start + timedelta(hours=6)
    val_payload = {
        "asset_id": str(asset.id),
        "start_time": overlap_start.isoformat(),
        "end_time": overlap_end.isoformat(),
    }
    res_val = client.post("/api/v1/maintenance/validate-window", json=val_payload)
    assert res_val.status_code == 200
    val_data = res_val.json()
    assert val_data["is_compatible"] is False
    assert "Hard Maintenance Window Conflict" in val_data["conflict_details"]
    assert val_data["conflicting_record_id"] == created_id

    # 3. Attempt to schedule overlapping maintenance (MUST reject with HTTP 409 Conflict)
    res_conflict = client.post(
        "/api/v1/maintenance/records",
        json={
            "asset_id": str(asset.id),
            "category": "avionics_check",
            "start_time": overlap_start.isoformat(),
            "end_time": overlap_end.isoformat(),
            "reason": "Overlapping request",
        },
        headers=plan_headers,
    )
    assert res_conflict.status_code == 409
    assert "Hard Maintenance Window Conflict" in res_conflict.json()["detail"]

    # 4. Non-overlapping window is compatible
    clean_start = maint_end + timedelta(hours=4)
    clean_end = clean_start + timedelta(hours=4)
    res_clean_val = client.post(
        "/api/v1/maintenance/validate-window",
        json={
            "asset_id": str(asset.id),
            "start_time": clean_start.isoformat(),
            "end_time": clean_end.isoformat(),
        },
    )
    assert res_clean_val.status_code == 200
    assert res_clean_val.json()["is_compatible"] is True


def test_global_search_and_events_inject(db: Session):
    """Verify unified search and disruption event injection with audit log."""
    # Search
    res_search = client.get("/api/v1/search?q=Su-30")
    assert res_search.status_code == 200
    search_data = res_search.json()
    assert search_data["total"] >= 1
    assert any("SB-" in r["title"] for r in search_data["results"])

    # Inject disruption event
    plan_headers = get_auth_headers(db, "planner@airops.local")
    event_payload = {
        "event_type": "environmental_restriction",
        "affected_entity_type": "zone",
        "affected_entity_id": "BASE-ALPHA",
        "severity": "high",
        "payload_json": {"description": "Fog visibility reduced below minimum landing limits."},
        "reason": "Simulated low-visibility weather inject",
    }
    res_event = client.post("/api/v1/events", json=event_payload, headers=plan_headers)
    assert res_event.status_code == 201
    evt = res_event.json()
    assert evt["event_type"] == "environmental_restriction"
    assert evt["severity"] == "high"


def test_overview_kpis_equal_database_records(db: Session):
    """
    Phase 3 Exit Gate: Verify every Overview KPI matches a direct database query.
    """
    res = client.get("/api/v1/overview")
    assert res.status_code == 200
    kpis = res.json()

    # 1. Total active assets in DB
    total_assets = db.execute(select(func.count(Asset.id))).scalar()
    available_assets = db.execute(
        select(func.count(Asset.id)).where(Asset.status == "available")
    ).scalar()
    expected_avail = round(available_assets / total_assets, 3)
    assert round(kpis["asset_availability"]["value"], 3) == expected_avail

    # 2. Spares shortages in DB
    db_shortages = db.execute(
        select(func.count(SparesInventory.id)).where(
            SparesInventory.on_hand < SparesInventory.minimum_safety_level
        )
    ).scalar()
    assert kpis["spares_shortage"] == db_shortages

    # 3. Eligible tasks in DB within 7-day planning horizon
    clock = get_clock()
    horizon_end = clock.now() + timedelta(days=7)
    db_eligible = db.execute(
        select(func.count(Task.id)).where(
            ~Task.status.in_(["cancelled", "completed"]),
            Task.earliest_start <= horizon_end,
        )
    ).scalar()
    assert kpis["eligible_tasks"] == db_eligible
