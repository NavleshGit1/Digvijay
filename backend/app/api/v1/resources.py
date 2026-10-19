import uuid
from datetime import datetime
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.api.deps import get_clock, require_permission
from app.core.clock import Clock
from app.core.enums import UserRole
from app.db.session import get_db
from app.models.identity import User
from app.models.logistics import MaintenanceRule, Part, ResupplyOrder, SparesInventory
from app.models.operations import MaintenanceRecord, Task, TaskDependency, TaskExecution, TaskRequirement
from app.models.resources import Asset, Personnel, PersonnelQualification, Qualification, Zone
from app.schemas.resources import (
    AssetDetailOut,
    AssetOut,
    AssetUpdate,
    MaintenanceRecordCreate,
    MaintenanceRecordOut,
    MaintenanceValidationRequest,
    MaintenanceValidationResponse,
    PersonnelDetailOut,
    PersonnelOut,
    PersonnelQualificationOut,
    PersonnelUpdate,
    ResupplyOrderCreate,
    ResupplyOrderOut,
    SparesInventoryOut,
    TaskDetailOut,
    TaskOut,
    TaskRequirementOut,
    TaskUpdate,
    ZoneOut,
)
from app.services.audit import write_audit_entry
from app.services.maintenance_validation import validate_maintenance_overlap

router = APIRouter(tags=["resources"])


# ==========================================
# Zones
# ==========================================

@router.get("/zones", response_model=list[ZoneOut])
def list_zones(db: Session = Depends(get_db)) -> list[Zone]:
    """Retrieve all operational airbases and sector zones."""
    stmt = select(Zone).order_by(Zone.code.asc())
    return list(db.execute(stmt).scalars().all())


# ==========================================
# Assets
# ==========================================

@router.get("/assets", response_model=list[AssetOut])
def list_assets(
    asset_type: str | None = Query(None, description="Filter by asset type"),
    asset_status: str | None = Query(None, alias="status", description="Filter by status"),
    zone_id: uuid.UUID | None = Query(None, description="Filter by zone ID"),
    min_health: float | None = Query(None, ge=0.0, le=1.0, description="Minimum health score"),
    search: str | None = Query(None, description="Search identifier or model name"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    clock: Clock = Depends(get_clock),
) -> list[AssetOut]:
    """List fleet assets with filtering, sorting, and pagination."""
    stmt = select(Asset).options(joinedload(Asset.zone))

    if asset_type:
        stmt = stmt.where(Asset.asset_type == asset_type)
    if asset_status:
        stmt = stmt.where(Asset.status == asset_status)
    if zone_id:
        stmt = stmt.where(Asset.zone_id == zone_id)
    if min_health is not None:
        stmt = stmt.where(Asset.health_score >= min_health)
    if search:
        search_fmt = f"%{search.strip()}%"
        stmt = stmt.where(or_(Asset.identifier.ilike(search_fmt), Asset.model_name.ilike(search_fmt)))

    stmt = stmt.order_by(Asset.identifier.asc()).offset(skip).limit(limit)
    assets = db.execute(stmt).scalars().all()

    # Pre-fetch active maintenance IDs
    now = clock.now()
    active_maint_stmt = select(MaintenanceRecord.asset_id).where(
        MaintenanceRecord.status.in_(["scheduled", "in_progress"]),
        MaintenanceRecord.start_time <= now,
        MaintenanceRecord.end_time >= now,
    )
    active_asset_ids = set(db.execute(active_maint_stmt).scalars().all())

    results = []
    for a in assets:
        results.append(
            AssetOut(
                id=a.id,
                identifier=a.identifier,
                asset_type=a.asset_type,
                model_name=a.model_name,
                status=a.status,
                health_score=round(a.health_score, 3),
                zone_id=a.zone_id,
                zone_code=a.zone.code if a.zone else "UNKNOWN",
                zone_name=a.zone.name if a.zone else "Unknown Base",
                current_location=a.current_location,
                flight_hours=round(a.flight_hours, 1),
                cycles=a.cycles,
                has_active_maintenance=a.id in active_asset_ids,
            )
        )
    return results


@router.get("/assets/{asset_id}", response_model=AssetDetailOut)
def get_asset_detail(
    asset_id: uuid.UUID,
    db: Session = Depends(get_db),
    clock: Clock = Depends(get_clock),
) -> AssetDetailOut:
    """Retrieve detailed asset metrics, health breakdown, and maintenance work orders."""
    asset = db.execute(select(Asset).options(joinedload(Asset.zone)).where(Asset.id == asset_id)).scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Asset '{asset_id}' not found.")

    now = clock.now()
    maint_stmt = (
        select(MaintenanceRecord)
        .where(MaintenanceRecord.asset_id == asset_id)
        .order_by(MaintenanceRecord.start_time.desc())
        .limit(10)
    )
    records = db.execute(maint_stmt).scalars().all()

    maint_outs = [
        MaintenanceRecordOut(
            id=r.id,
            asset_id=r.asset_id,
            asset_identifier=asset.identifier,
            category=r.category,
            start_time=r.start_time,
            end_time=r.end_time,
            predicted_completion=r.predicted_completion,
            is_unplanned=r.is_unplanned,
            status=r.status,
            is_overdue=r.status != "completed" and r.end_time < now,
        )
        for r in records
    ]

    has_active = any(r.status in ["scheduled", "in_progress"] and r.start_time <= now <= r.end_time for r in records)

    return AssetDetailOut(
        id=asset.id,
        identifier=asset.identifier,
        asset_type=asset.asset_type,
        model_name=asset.model_name,
        status=asset.status,
        health_score=round(asset.health_score, 3),
        zone_id=asset.zone_id,
        zone_code=asset.zone.code if asset.zone else "UNKNOWN",
        zone_name=asset.zone.name if asset.zone else "Unknown Base",
        current_location=asset.current_location,
        flight_hours=round(asset.flight_hours, 1),
        cycles=asset.cycles,
        has_active_maintenance=has_active,
        recent_maintenance=maint_outs,
        usage_summary={
            "flight_hours_since_last_service": round(asset.flight_hours % 100.0, 1),
            "cycles_since_last_service": asset.cycles % 50,
            "next_scheduled_inspection": "100-Hour Periodic Inspection",
        },
    )


@router.patch("/assets/{asset_id}", response_model=AssetOut)
def update_asset(
    asset_id: uuid.UUID,
    payload: AssetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission([UserRole.PLANNER, UserRole.ADMIN])),
    clock: Clock = Depends(get_clock),
) -> AssetOut:
    """Update asset status, location, or health score with mandatory audit justification."""
    asset = db.execute(select(Asset).options(joinedload(Asset.zone)).where(Asset.id == asset_id)).scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Asset '{asset_id}' not found.")

    before_state = {
        "status": asset.status,
        "current_location": asset.current_location,
        "zone_id": str(asset.zone_id),
        "health_score": asset.health_score,
    }

    if payload.status is not None:
        asset.status = payload.status
    if payload.current_location is not None:
        asset.current_location = payload.current_location
    if payload.zone_id is not None:
        zone = db.get(Zone, payload.zone_id)
        if not zone:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Zone '{payload.zone_id}' not found.")
        asset.zone_id = payload.zone_id
    if payload.health_score is not None:
        asset.health_score = max(0.0, min(1.0, payload.health_score))

    after_state = {
        "status": asset.status,
        "current_location": asset.current_location,
        "zone_id": str(asset.zone_id),
        "health_score": asset.health_score,
    }

    user_role = current_user.roles[0].name if current_user.roles else "planner"
    write_audit_entry(
        db=db,
        actor_id=current_user.id,
        role=user_role,
        action="UPDATE_ASSET",
        entity_type="asset",
        entity_id=str(asset.id),
        reason=payload.reason,
        before_state=before_state,
        after_state=after_state,
    )
    db.commit()
    db.refresh(asset)

    return AssetOut(
        id=asset.id,
        identifier=asset.identifier,
        asset_type=asset.asset_type,
        model_name=asset.model_name,
        status=asset.status,
        health_score=round(asset.health_score, 3),
        zone_id=asset.zone_id,
        zone_code=asset.zone.code if asset.zone else "UNKNOWN",
        zone_name=asset.zone.name if asset.zone else "Unknown Base",
        current_location=asset.current_location,
        flight_hours=round(asset.flight_hours, 1),
        cycles=asset.cycles,
        has_active_maintenance=False,
    )


# ==========================================
# Personnel
# ==========================================

@router.get("/personnel", response_model=list[PersonnelOut])
def list_personnel(
    role_type: str | None = Query(None, description="Filter by role type (pilot, maintenance_tech, wso)"),
    status_filter: str | None = Query(None, alias="status", description="Filter by status"),
    zone_id: uuid.UUID | None = Query(None, description="Filter by home zone ID"),
    search: str | None = Query(None, description="Search name or callsign"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[PersonnelOut]:
    """List operational personnel with certifications and home zone details."""
    stmt = (
        select(Personnel)
        .options(
            joinedload(Personnel.home_zone),
            selectinload(Personnel.qualifications).joinedload(PersonnelQualification.qualification),
        )
    )

    if role_type:
        stmt = stmt.where(Personnel.role_type == role_type)
    if status_filter:
        stmt = stmt.where(Personnel.status == status_filter)
    if zone_id:
        stmt = stmt.where(Personnel.home_zone_id == zone_id)
    if search:
        search_fmt = f"%{search.strip()}%"
        stmt = stmt.where(or_(Personnel.name.ilike(search_fmt), Personnel.callsign.ilike(search_fmt)))

    stmt = stmt.order_by(Personnel.name.asc()).offset(skip).limit(limit)
    rows = db.execute(stmt).scalars().all()

    results = []
    for p in rows:
        quals = [pq.qualification.code for pq in p.qualifications if pq.qualification]
        results.append(
            PersonnelOut(
                id=p.id,
                name=p.name,
                callsign=p.callsign,
                role_type=p.role_type,
                status=p.status,
                duty_hours_accumulated=round(p.duty_hours_accumulated, 1),
                home_zone_id=p.home_zone_id,
                home_zone_name=p.home_zone.name if p.home_zone else "Unknown Base",
                qualifications=quals,
            )
        )
    return results


@router.get("/personnel/{personnel_id}", response_model=PersonnelDetailOut)
def get_personnel_detail(
    personnel_id: uuid.UUID,
    db: Session = Depends(get_db),
    clock: Clock = Depends(get_clock),
) -> PersonnelDetailOut:
    """Retrieve detailed personnel dossier including certification validity dates."""
    stmt = (
        select(Personnel)
        .options(
            joinedload(Personnel.home_zone),
            selectinload(Personnel.qualifications).joinedload(PersonnelQualification.qualification),
        )
        .where(Personnel.id == personnel_id)
    )
    p = db.execute(stmt).scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Personnel '{personnel_id}' not found.")

    now = clock.now()
    qual_details = []
    qual_codes = []
    for pq in p.qualifications:
        if pq.qualification:
            qual_codes.append(pq.qualification.code)
            qual_details.append(
                PersonnelQualificationOut(
                    qualification_code=pq.qualification.code,
                    qualification_name=pq.qualification.name,
                    acquired_at=pq.acquired_at,
                    expires_at=pq.expires_at,
                    is_expired=pq.expires_at < now,
                )
            )

    return PersonnelDetailOut(
        id=p.id,
        name=p.name,
        callsign=p.callsign,
        role_type=p.role_type,
        status=p.status,
        duty_hours_accumulated=round(p.duty_hours_accumulated, 1),
        home_zone_id=p.home_zone_id,
        home_zone_name=p.home_zone.name if p.home_zone else "Unknown Base",
        qualifications=qual_codes,
        qualification_details=qual_details,
    )


@router.patch("/personnel/{personnel_id}", response_model=PersonnelOut)
def update_personnel(
    personnel_id: uuid.UUID,
    payload: PersonnelUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission([UserRole.PLANNER, UserRole.ADMIN])),
) -> PersonnelOut:
    """Update personnel operational readiness and duty hours with mandatory audit justification."""
    stmt = (
        select(Personnel)
        .options(
            joinedload(Personnel.home_zone),
            selectinload(Personnel.qualifications).joinedload(PersonnelQualification.qualification),
        )
        .where(Personnel.id == personnel_id)
    )
    p = db.execute(stmt).scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Personnel '{personnel_id}' not found.")

    before_state = {
        "status": p.status,
        "duty_hours_accumulated": p.duty_hours_accumulated,
        "home_zone_id": str(p.home_zone_id),
    }

    if payload.status is not None:
        p.status = payload.status
    if payload.duty_hours_accumulated is not None:
        p.duty_hours_accumulated = max(0.0, payload.duty_hours_accumulated)
    if payload.home_zone_id is not None:
        zone = db.get(Zone, payload.home_zone_id)
        if not zone:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Zone '{payload.home_zone_id}' not found.")
        p.home_zone_id = payload.home_zone_id

    after_state = {
        "status": p.status,
        "duty_hours_accumulated": p.duty_hours_accumulated,
        "home_zone_id": str(p.home_zone_id),
    }

    user_role = current_user.roles[0].name if current_user.roles else "planner"
    write_audit_entry(
        db=db,
        actor_id=current_user.id,
        role=user_role,
        action="UPDATE_PERSONNEL",
        entity_type="personnel",
        entity_id=str(p.id),
        reason=payload.reason,
        before_state=before_state,
        after_state=after_state,
    )
    db.commit()
    db.refresh(p)

    quals = [pq.qualification.code for pq in p.qualifications if pq.qualification]
    return PersonnelOut(
        id=p.id,
        name=p.name,
        callsign=p.callsign,
        role_type=p.role_type,
        status=p.status,
        duty_hours_accumulated=round(p.duty_hours_accumulated, 1),
        home_zone_id=p.home_zone_id,
        home_zone_name=p.home_zone.name if p.home_zone else "Unknown Base",
        qualifications=quals,
    )


# ==========================================
# Tasks
# ==========================================

@router.get("/tasks", response_model=list[TaskOut])
def list_tasks(
    task_status: str | None = Query(None, alias="status", description="Filter by task status"),
    priority: str | None = Query(None, description="Filter by priority"),
    category: str | None = Query(None, description="Filter by category"),
    zone_id: uuid.UUID | None = Query(None, description="Filter by zone ID"),
    search: str | None = Query(None, description="Search task code"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[TaskOut]:
    """List operational flight tasks, sorties, and maintenance work items."""
    stmt = select(Task).options(selectinload(Task.requirements))

    if task_status:
        stmt = stmt.where(Task.status == task_status)
    if priority:
        stmt = stmt.where(Task.priority == priority)
    if category:
        stmt = stmt.where(Task.category == category)
    if zone_id:
        stmt = stmt.where(Task.zone_id == zone_id)
    if search:
        stmt = stmt.where(Task.code.ilike(f"%{search.strip()}%"))

    stmt = stmt.order_by(Task.earliest_start.asc()).offset(skip).limit(limit)
    tasks = db.execute(stmt).scalars().all()

    # Pre-fetch zone map
    zone_map = {z.id: z.name for z in db.execute(select(Zone)).scalars().all()}

    results = []
    for t in tasks:
        reqs = [
            TaskRequirementOut(
                asset_type_required=r.asset_type_required,
                crew_headcount=r.crew_headcount,
                required_qualification_code=r.required_qualification_code,
            )
            for r in t.requirements
        ]
        results.append(
            TaskOut(
                id=t.id,
                code=t.code,
                category=t.category,
                zone_id=t.zone_id,
                zone_name=zone_map.get(t.zone_id, "Unknown Zone"),
                earliest_start=t.earliest_start,
                latest_end=t.latest_end,
                duration_minutes=t.duration_minutes,
                priority=t.priority,
                weight=round(t.weight, 2),
                status=t.status,
                requirements=reqs,
            )
        )
    return results


@router.get("/tasks/{task_id}", response_model=TaskDetailOut)
def get_task_detail(task_id: uuid.UUID, db: Session = Depends(get_db)) -> TaskDetailOut:
    """Retrieve detailed task data including DAG precedence dependencies."""
    stmt = (
        select(Task)
        .options(
            selectinload(Task.requirements),
            selectinload(Task.predecessors).joinedload(TaskDependency.predecessor),
            selectinload(Task.successors).joinedload(TaskDependency.successor),
        )
        .where(Task.id == task_id)
    )
    t = db.execute(stmt).scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task '{task_id}' not found.")

    zone = db.get(Zone, t.zone_id)
    zone_name = zone.name if zone else "Unknown Zone"

    reqs = [
        TaskRequirementOut(
            asset_type_required=r.asset_type_required,
            crew_headcount=r.crew_headcount,
            required_qualification_code=r.required_qualification_code,
        )
        for r in t.requirements
    ]

    preds = [
        {"predecessor_id": str(d.predecessor_id), "predecessor_code": d.predecessor.code if d.predecessor else "UNK", "min_lag_minutes": d.min_lag_minutes}
        for d in t.predecessors
    ]
    succs = [
        {"successor_id": str(d.successor_id), "successor_code": d.successor.code if d.successor else "UNK", "min_lag_minutes": d.min_lag_minutes}
        for d in t.successors
    ]

    return TaskDetailOut(
        id=t.id,
        code=t.code,
        category=t.category,
        zone_id=t.zone_id,
        zone_name=zone_name,
        earliest_start=t.earliest_start,
        latest_end=t.latest_end,
        duration_minutes=t.duration_minutes,
        priority=t.priority,
        weight=round(t.weight, 2),
        status=t.status,
        requirements=reqs,
        predecessors=preds,
        successors=succs,
    )


@router.patch("/tasks/{task_id}", response_model=TaskOut)
def update_task_status(
    task_id: uuid.UUID,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission([UserRole.PLANNER, UserRole.ADMIN])),
) -> TaskOut:
    """Update task lifecycle state (e.g. cancelled, in_progress, completed) with mandatory audit log."""
    t = db.execute(select(Task).options(selectinload(Task.requirements)).where(Task.id == task_id)).scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Task '{task_id}' not found.")

    before_state = {"status": t.status}
    if payload.status is not None:
        t.status = payload.status
    after_state = {"status": t.status}

    user_role = current_user.roles[0].name if current_user.roles else "planner"
    write_audit_entry(
        db=db,
        actor_id=current_user.id,
        role=user_role,
        action="UPDATE_TASK",
        entity_type="task",
        entity_id=str(t.id),
        reason=payload.reason,
        before_state=before_state,
        after_state=after_state,
    )
    db.commit()
    db.refresh(t)

    zone = db.get(Zone, t.zone_id)
    reqs = [
        TaskRequirementOut(
            asset_type_required=r.asset_type_required,
            crew_headcount=r.crew_headcount,
            required_qualification_code=r.required_qualification_code,
        )
        for r in t.requirements
    ]
    return TaskOut(
        id=t.id,
        code=t.code,
        category=t.category,
        zone_id=t.zone_id,
        zone_name=zone.name if zone else "Unknown Zone",
        earliest_start=t.earliest_start,
        latest_end=t.latest_end,
        duration_minutes=t.duration_minutes,
        priority=t.priority,
        weight=round(t.weight, 2),
        status=t.status,
        requirements=reqs,
    )


# ==========================================
# Spares & Logistics
# ==========================================

@router.get("/inventory/spares", response_model=list[SparesInventoryOut])
def list_spares_inventory(
    zone_id: uuid.UUID | None = Query(None, description="Filter by zone ID"),
    shortage_only: bool = Query(False, description="Filter to items below safety threshold"),
    category: str | None = Query(None, description="Filter by part category"),
    db: Session = Depends(get_db),
) -> list[SparesInventoryOut]:
    """Retrieve spares stock levels across operating bases with safety buffer alerts."""
    stmt = select(SparesInventory).options(joinedload(SparesInventory.part))

    if zone_id:
        stmt = stmt.where(SparesInventory.zone_id == zone_id)
    if shortage_only:
        stmt = stmt.where(SparesInventory.on_hand < SparesInventory.minimum_safety_level)
    if category:
        stmt = stmt.join(Part).where(Part.category == category)

    stmt = stmt.order_by(SparesInventory.on_hand.asc())
    rows = db.execute(stmt).scalars().all()

    zone_map = {z.id: z.name for z in db.execute(select(Zone)).scalars().all()}

    results = []
    for s in rows:
        results.append(
            SparesInventoryOut(
                id=s.id,
                part_id=s.part_id,
                part_number=s.part.part_number if s.part else "UNKNOWN",
                part_name=s.part.name if s.part else "Unknown Part",
                category=s.part.category if s.part else "general",
                zone_id=s.zone_id,
                zone_name=zone_map.get(s.zone_id, "Unknown Zone"),
                on_hand=s.on_hand,
                reserved=s.reserved,
                minimum_safety_level=s.minimum_safety_level,
                is_shortage=s.on_hand < s.minimum_safety_level,
            )
        )
    return results


@router.post("/inventory/orders", response_model=ResupplyOrderOut, status_code=status.HTTP_201_CREATED)
def create_resupply_order(
    payload: ResupplyOrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission([UserRole.PLANNER, UserRole.ADMIN])),
    clock: Clock = Depends(get_clock),
) -> ResupplyOrderOut:
    """Create an expedited spares resupply order with lead-time tracking and audit log."""
    part = db.get(Part, payload.part_id)
    if not part:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Part '{payload.part_id}' not found.")
    zone = db.get(Zone, payload.zone_id)
    if not zone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Zone '{payload.zone_id}' not found.")

    from datetime import timedelta
    now = clock.now()
    estimated_arrival = now + timedelta(days=2)

    order = ResupplyOrder(
        part_id=payload.part_id,
        zone_id=payload.zone_id,
        quantity=payload.quantity,
        ordered_at=now,
        estimated_arrival=estimated_arrival,
        status="in_transit",
    )
    db.add(order)
    db.flush()

    user_role = current_user.roles[0].name if current_user.roles else "planner"
    write_audit_entry(
        db=db,
        actor_id=current_user.id,
        role=user_role,
        action="ORDER_SPARES",
        entity_type="resupply_order",
        entity_id=str(order.id),
        reason=payload.reason,
        before_state=None,
        after_state={
            "part_number": part.part_number,
            "zone_code": zone.code,
            "quantity": payload.quantity,
            "estimated_arrival": estimated_arrival.isoformat(),
        },
    )
    db.commit()
    db.refresh(order)

    return ResupplyOrderOut(
        id=order.id,
        part_id=order.part_id,
        part_number=part.part_number,
        part_name=part.name,
        zone_id=order.zone_id,
        zone_name=zone.name,
        quantity=order.quantity,
        ordered_at=order.ordered_at,
        estimated_arrival=order.estimated_arrival,
        status=order.status,
    )


# ==========================================
# Maintenance & Conflict Validation
# ==========================================

@router.get("/maintenance/records", response_model=list[MaintenanceRecordOut])
def list_maintenance_records(
    asset_id: uuid.UUID | None = Query(None, description="Filter by asset ID"),
    maint_status: str | None = Query(None, alias="status", description="Filter by status"),
    is_unplanned: bool | None = Query(None, description="Filter unplanned work orders"),
    overdue_only: bool = Query(False, description="Filter overdue work orders"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    clock: Clock = Depends(get_clock),
) -> list[MaintenanceRecordOut]:
    """Retrieve maintenance work orders and schedule tracking."""
    stmt = select(MaintenanceRecord)

    if asset_id:
        stmt = stmt.where(MaintenanceRecord.asset_id == asset_id)
    if maint_status:
        stmt = stmt.where(MaintenanceRecord.status == maint_status)
    if is_unplanned is not None:
        stmt = stmt.where(MaintenanceRecord.is_unplanned == is_unplanned)

    now = clock.now()
    if overdue_only:
        stmt = stmt.where(
            MaintenanceRecord.status != "completed",
            MaintenanceRecord.end_time < now,
        )

    stmt = stmt.order_by(MaintenanceRecord.start_time.asc()).offset(skip).limit(limit)
    records = db.execute(stmt).scalars().all()

    # Pre-fetch asset map
    asset_map = {a.id: a.identifier for a in db.execute(select(Asset)).scalars().all()}

    results = []
    for r in records:
        results.append(
            MaintenanceRecordOut(
                id=r.id,
                asset_id=r.asset_id,
                asset_identifier=asset_map.get(r.asset_id, "UNKNOWN"),
                category=r.category,
                start_time=r.start_time,
                end_time=r.end_time,
                predicted_completion=r.predicted_completion,
                is_unplanned=r.is_unplanned,
                status=r.status,
                is_overdue=r.status != "completed" and r.end_time < now,
            )
        )
    return results


@router.post("/maintenance/records", response_model=MaintenanceRecordOut, status_code=status.HTTP_201_CREATED)
def create_maintenance_record(
    payload: MaintenanceRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission([UserRole.PLANNER, UserRole.ADMIN])),
    clock: Clock = Depends(get_clock),
) -> MaintenanceRecordOut:
    """
    Schedule maintenance work order with Hard Maintenance Window conflict validation (P3-2).
    Rejects overlapping maintenance or assignments.
    """
    asset = db.get(Asset, payload.asset_id)
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Asset '{payload.asset_id}' not found.")

    is_compat, conflict_msg, _ = validate_maintenance_overlap(
        db=db,
        asset_id=payload.asset_id,
        start_time=payload.start_time,
        end_time=payload.end_time,
    )
    if not is_compat:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=conflict_msg)

    record = MaintenanceRecord(
        asset_id=payload.asset_id,
        category=payload.category,
        start_time=payload.start_time,
        end_time=payload.end_time,
        predicted_completion=payload.end_time,
        is_unplanned=payload.is_unplanned,
        status="scheduled",
    )
    db.add(record)
    db.flush()

    user_role = current_user.roles[0].name if current_user.roles else "planner"
    write_audit_entry(
        db=db,
        actor_id=current_user.id,
        role=user_role,
        action="SCHEDULE_MAINTENANCE",
        entity_type="maintenance_record",
        entity_id=str(record.id),
        reason=payload.reason,
        before_state=None,
        after_state={
            "asset_identifier": asset.identifier,
            "category": payload.category,
            "start_time": payload.start_time.isoformat(),
            "end_time": payload.end_time.isoformat(),
            "is_unplanned": payload.is_unplanned,
        },
    )
    db.commit()
    db.refresh(record)

    now = clock.now()
    return MaintenanceRecordOut(
        id=record.id,
        asset_id=record.asset_id,
        asset_identifier=asset.identifier,
        category=record.category,
        start_time=record.start_time,
        end_time=record.end_time,
        predicted_completion=record.predicted_completion,
        is_unplanned=record.is_unplanned,
        status=record.status,
        is_overdue=record.status != "completed" and record.end_time < now,
    )


@router.post("/maintenance/validate-window", response_model=MaintenanceValidationResponse)
def validate_window(
    payload: MaintenanceValidationRequest,
    db: Session = Depends(get_db),
) -> MaintenanceValidationResponse:
    """Validate whether an asset can be scheduled or assigned during a proposed time window."""
    is_compat, conflict_msg, conflicting_record = validate_maintenance_overlap(
        db=db,
        asset_id=payload.asset_id,
        start_time=payload.start_time,
        end_time=payload.end_time,
    )
    return MaintenanceValidationResponse(
        is_compatible=is_compat,
        conflict_details=conflict_msg,
        conflicting_record_id=conflicting_record.id if conflicting_record else None,
    )


@router.delete("/maintenance/records/{record_id}", status_code=status.HTTP_200_OK)
def delete_maintenance_record(
    record_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission([UserRole.ADMIN])),
) -> dict[str, Any]:
    """Cancels/removes a maintenance record (Admin only, audited)."""
    record = db.get(MaintenanceRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Maintenance record not found")

    db.delete(record)
    write_audit_entry(
        db=db,
        actor_id=current_user.id,
        role="admin",
        action="CANCEL_MAINTENANCE",
        entity_type="maintenance_record",
        entity_id=str(record_id),
        reason=f"Admin deleted maintenance record {record_id}",
    )
    db.commit()
    return {"id": str(record_id), "status": "deleted"}

