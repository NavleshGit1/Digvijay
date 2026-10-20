"""Optimisation and Scheduling API Endpoints (Phase 4, Tasks P4-6 & P4-7)."""
from datetime import datetime
from typing import Any
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.core.clock import get_clock
from app.core.enums import ClockMode, JobState, PlanKind, PlanSource, PlanStatus, SolverStatus, UserRole
from app.api.deps import require_permission
from app.db.session import get_db
from app.models.identity import User
from app.models.jobs import Job
from app.models.operations import MaintenanceRecord, Task
from app.models.plans import ObjectiveWeightSet, Plan, PlanAssignment, PlanValidation, PlanVersion
from app.models.resources import Asset, Personnel
from app.services.audit import write_audit_entry
from app.services.optimisation import OptimisationService
from app.worker.tasks import run_optimisation_job, run_replan_job

router = APIRouter(tags=["Optimisation & Scheduling"])


class OptimisationJobRequest(BaseModel):
    model_config = {"protected_namespaces": ()}

    job_type: str = Field(default="optimise", description="'baseline' or 'optimise'")
    plan_name: str = Field(default="Operational Master Plan 2026")
    time_limit_seconds: float = Field(default=15.0, ge=0.01, le=300.0)
    seed: int = Field(default=42)
    weight_set_version: int = Field(default=1)
    as_of: datetime | None = None
    run_async: bool = Field(default=True, description="Execute in background worker or synchronously")


class ReplanJobRequest(BaseModel):
    model_config = {"protected_namespaces": ()}

    plan_id: uuid.UUID | None = None
    frozen_window_minutes: int = Field(default=120, ge=0, le=1440)
    disruption_reason: str = Field(default="Operational disruption replan", max_length=255)
    time_limit_seconds: float = Field(default=15.0, ge=0.01, le=300.0)
    seed: int = Field(default=42)
    weight_set_version: int = Field(default=1)
    as_of: datetime | None = None
    run_async: bool = Field(default=True, description="Execute in background worker or synchronously")


class RollingHorizonRequest(BaseModel):
    model_config = {"protected_namespaces": ()}

    advance_minutes: int = Field(default=60, ge=1, le=1440)
    frozen_window_minutes: int = Field(default=120, ge=0, le=1440)
    plan_id: uuid.UUID | None = None
    time_limit_seconds: float = Field(default=15.0, ge=0.01, le=300.0)
    seed: int = Field(default=42)
    weight_set_version: int = Field(default=1)
    run_async: bool = Field(default=False, description="Execute in background worker or synchronously")


class WeightSetCreateRequest(BaseModel):
    name: str = Field(default="Operational Weights Custom", max_length=100)
    delay_weight: int = Field(default=10, ge=0)
    completion_weight: int = Field(default=1000, ge=0)
    churn_weight: int = Field(default=50, ge=0)
    balance_weight: int = Field(default=5, ge=0)
    buffer_weight: int = Field(default=20, ge=0)


@router.post("/optimisation/jobs", status_code=status.HTTP_202_ACCEPTED)
def create_optimisation_job(
    req: OptimisationJobRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission([UserRole.PLANNER, UserRole.ADMIN])),
) -> dict[str, Any]:
    """Triggers a Baseline W-EDD or CP-SAT optimisation job with progress streaming."""
    clock_as_of = req.as_of or get_clock().as_of()

    job_uuid = uuid.uuid4()
    job = Job(
        id=job_uuid,
        job_type=f"optimisation_{req.job_type}",
        state=JobState.QUEUED.value,
        progress_percent=0.0,
        message=f"Queued {req.job_type} scheduling job (seed={req.seed}, limit={req.time_limit_seconds}s)",
    )
    db.add(job)
    db.commit()

    params = {
        "job_type": req.job_type,
        "plan_name": req.plan_name,
        "time_limit_seconds": req.time_limit_seconds,
        "seed": req.seed,
        "weight_set_version": req.weight_set_version,
        "as_of": clock_as_of.isoformat(),
    }

    if req.run_async:
        run_optimisation_job.delay(str(job_uuid), params)
        return {
            "job_id": str(job_uuid),
            "job_type": req.job_type,
            "state": JobState.QUEUED.value,
            "message": "Job queued for asynchronous background execution via Celery",
        }
    else:
        service = OptimisationService(db)
        result = service.execute_optimisation_job(
            job_id_str=str(job_uuid),
            job_type=req.job_type,
            plan_name=req.plan_name,
            time_limit_seconds=req.time_limit_seconds,
            seed=req.seed,
            weight_set_version=req.weight_set_version,
            as_of=clock_as_of,
        )
        return {
            "job_id": str(job_uuid),
            "job_type": req.job_type,
            "state": JobState.COMPLETED.value,
            "result": result,
        }


@router.get("/optimisation/jobs/{job_id}")
def get_optimisation_job_status(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission([UserRole.PLANNER, UserRole.REVIEWER, UserRole.ANALYST, UserRole.ADMIN])),
) -> dict[str, Any]:
    """Retrieves current job status, execution progress percentage, and results."""
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    job = db.execute(select(Job).where(Job.id == job_uuid)).scalars().first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    plan_version_data = None
    if job.state == JobState.COMPLETED.value and job.result_id:
        try:
            res_uuid = uuid.UUID(job.result_id)
            pv = db.execute(select(PlanVersion).where(PlanVersion.id == res_uuid)).scalars().first()
            if pv:
                plan_version_data = {
                    "plan_id": str(pv.plan_id),
                    "version_number": pv.version_number,
                    "kind": pv.kind,
                    "status": pv.status,
                    "solver_status": pv.solver_status,
                    "runtime_seconds": pv.solver_runtime_seconds,
                    "metrics": pv.metrics_json,
                }
        except Exception:
            pass

    return {
        "job_id": str(job.id),
        "job_type": job.job_type,
        "state": job.state,
        "progress_percent": job.progress_percent,
        "message": job.message,
        "result_id": job.result_id,
        "plan_version": plan_version_data,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
    }


@router.post("/optimisation/jobs/{job_id}/cancel")
def cancel_optimisation_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission([UserRole.PLANNER, UserRole.ADMIN])),
) -> dict[str, Any]:
    """Cancels a queued or running optimisation job."""
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")

    job = db.execute(select(Job).where(Job.id == job_uuid)).scalars().first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.state in (JobState.QUEUED.value, JobState.RUNNING.value):
        job.state = JobState.CANCELLED.value
        job.message = f"Job cancelled by user {current_user.email}"
        db.commit()

    return {"job_id": job_id, "state": job.state, "message": "Job cancellation processed"}


@router.get("/plans")
def list_plans(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission([UserRole.PLANNER, UserRole.REVIEWER, UserRole.ANALYST, UserRole.ADMIN])),
) -> list[dict[str, Any]]:
    """Lists all logical plans with their version iterations."""
    plans = db.execute(select(Plan).order_by(Plan.created_at.desc())).scalars().all()
    results = []
    for p in plans:
        versions = (
            db.execute(select(PlanVersion).where(PlanVersion.plan_id == p.id).order_by(PlanVersion.version_number.desc()))
            .scalars()
            .all()
        )
        approved_version_num = None
        if p.current_approved_version_id:
            for v in versions:
                if v.id == p.current_approved_version_id:
                    approved_version_num = v.version_number
                    break

        results.append({
            "id": str(p.id),
            "name": p.name,
            "current_approved_version_id": str(p.current_approved_version_id) if p.current_approved_version_id else None,
            "current_approved_version": approved_version_num,
            "versions_count": len(versions),
            "latest_version": versions[0].version_number if versions else 0,
            "latest_solver_status": versions[0].solver_status if versions else None,
            "latest_kind": versions[0].kind if versions else None,
            "latest_status": versions[0].status if versions else None,
            "versions": [
                {
                    "version_number": v.version_number,
                    "kind": v.kind,
                    "status": v.status,
                    "solver_status": v.solver_status,
                    "plan_source": v.plan_source,
                    "based_on_version": v.based_on_version,
                    "stale_reason": v.stale_reason,
                    "refreshed_from": v.refreshed_from,
                    "rollback_target": v.rollback_target,
                    "metrics": v.metrics_json or {},
                    "runtime_seconds": v.solver_runtime_seconds,
                    "created_at": v.created_at.isoformat(),
                }
                for v in versions
            ],
            "created_at": p.created_at.isoformat(),
        })
    return results


@router.get("/plans/{plan_id}")
def get_plan_by_id(
    plan_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission([UserRole.PLANNER, UserRole.REVIEWER, UserRole.ANALYST, UserRole.ADMIN])),
) -> dict[str, Any]:
    """Returns plan overview and version summary for a specific plan."""
    try:
        p_uuid = uuid.UUID(plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan UUID")

    plan = db.execute(select(Plan).where(Plan.id == p_uuid)).scalars().first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    versions = (
        db.execute(select(PlanVersion).where(PlanVersion.plan_id == p_uuid).order_by(PlanVersion.version_number.desc()))
        .scalars()
        .all()
    )

    approved_version_num = None
    if plan.current_approved_version_id:
        for v in versions:
            if v.id == plan.current_approved_version_id:
                approved_version_num = v.version_number
                break

    return {
        "id": str(plan.id),
        "name": plan.name,
        "current_approved_version_id": str(plan.current_approved_version_id) if plan.current_approved_version_id else None,
        "current_approved_version": approved_version_num,
        "versions_count": len(versions),
        "latest_version": versions[0].version_number if versions else 0,
        "latest_solver_status": versions[0].solver_status if versions else None,
        "latest_kind": versions[0].kind if versions else None,
        "latest_status": versions[0].status if versions else None,
        "versions": [
            {
                "version_number": v.version_number,
                "kind": v.kind,
                "status": v.status,
                "solver_status": v.solver_status,
                "plan_source": v.plan_source,
                "based_on_version": v.based_on_version,
                "stale_reason": v.stale_reason,
                "refreshed_from": v.refreshed_from,
                "rollback_target": v.rollback_target,
                "metrics": v.metrics_json or {},
                "runtime_seconds": v.solver_runtime_seconds,
                "created_at": v.created_at.isoformat(),
            }
            for v in versions
        ],
        "created_at": plan.created_at.isoformat(),
    }


@router.get("/plans/{plan_id}/versions/{version_number}")
def get_plan_version_details(
    plan_id: str,
    version_number: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission([UserRole.PLANNER, UserRole.REVIEWER, UserRole.ANALYST, UserRole.ADMIN])),
) -> dict[str, Any]:
    """Returns complete schedule dossier including validation result, metrics, and assignments."""
    try:
        p_uuid = uuid.UUID(plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan UUID")

    pv = (
        db.execute(
            select(PlanVersion).where(PlanVersion.plan_id == p_uuid, PlanVersion.version_number == version_number)
        )
        .scalars()
        .first()
    )
    if not pv:
        raise HTTPException(status_code=404, detail=f"Plan version {version_number} not found for plan {plan_id}")

    # Validation result
    pv_val = db.execute(select(PlanValidation).where(PlanValidation.plan_version_id == pv.id)).scalars().first()

    # Assignments
    assignments = (
        db.execute(select(PlanAssignment).where(PlanAssignment.plan_version_id == pv.id).order_by(PlanAssignment.assigned_start.asc()))
        .scalars()
        .all()
    )

    # Fetch referenced tasks and assets in bulk
    task_ids = [a.task_id for a in assignments]
    asset_ids = [a.asset_id for a in assignments if a.asset_id]

    tasks_by_id = {t.id: t for t in db.execute(select(Task).where(Task.id.in_(task_ids))).scalars().all()} if task_ids else {}
    assets_by_id = {a.id: a for a in db.execute(select(Asset).where(Asset.id.in_(asset_ids))).scalars().all()} if asset_ids else {}

    assignment_items = []
    for asgn in assignments:
        t = tasks_by_id.get(asgn.task_id)
        a = assets_by_id.get(asgn.asset_id) if asgn.asset_id else None
        delay_mins = max(0.0, (asgn.assigned_end - t.latest_end).total_seconds() / 60.0) if t else 0.0

        assignment_items.append({
            "id": str(asgn.id),
            "task_id": str(asgn.task_id),
            "task_code": t.code if t else "UNKNOWN",
            "task_category": t.category if t else "sortie",
            "priority": t.priority if t else "routine",
            "asset_id": str(asgn.asset_id) if asgn.asset_id else None,
            "asset_identifier": a.identifier if a else "Unassigned",
            "asset_model": a.model_name if a else None,
            "personnel_ids": [str(p) for p in (asgn.personnel_ids or [])],
            "assigned_start": asgn.assigned_start.isoformat(),
            "assigned_end": asgn.assigned_end.isoformat(),
            "duration_minutes": t.duration_minutes if t else int((asgn.assigned_end - asgn.assigned_start).total_seconds() / 60),
            "delay_minutes": round(delay_mins, 1),
            "is_locked": asgn.is_locked,
        })

    return {
        "plan_id": str(pv.plan_id),
        "version_number": pv.version_number,
        "kind": pv.kind,
        "status": pv.status,
        "solver_status": pv.solver_status,
        "plan_source": pv.plan_source,
        "based_on_version": pv.based_on_version,
        "stale_reason": pv.stale_reason,
        "refreshed_from": pv.refreshed_from,
        "rollback_target": pv.rollback_target,
        "proposal_group_id": pv.proposal_group_id,
        "rejection_reason": pv.rejection_reason,
        "created_by": pv.created_by,
        "as_of": pv.as_of.isoformat(),
        "snapshot_hash": pv.snapshot_hash,
        "runtime_seconds": pv.solver_runtime_seconds,
        "metrics": pv.metrics_json or {},
        "manifest": pv.run_manifest_json or {},
        "validation": {
            "is_valid": pv_val.is_valid if pv_val else False,
            "violation_count": pv_val.violation_count if pv_val else 0,
            "violations": pv_val.violations_json if pv_val else [],
            "binding_constraints": pv_val.binding_constraints_json if pv_val else [],
            "validated_at": pv_val.validated_at.isoformat() if pv_val else None,
        },
        "assignments_count": len(assignment_items),
        "assignments": assignment_items,
    }



@router.get("/plans/{plan_id}/versions/{version_number}/gantt")
def get_plan_gantt_timeline(
    plan_id: str,
    version_number: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission([UserRole.PLANNER, UserRole.REVIEWER, UserRole.ANALYST, UserRole.ADMIN])),
) -> dict[str, Any]:
    """Returns formatted timeline tracks for interactive Gantt visualization (aircraft & crew tracks)."""
    try:
        p_uuid = uuid.UUID(plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid plan UUID")

    pv = (
        db.execute(
            select(PlanVersion).where(PlanVersion.plan_id == p_uuid, PlanVersion.version_number == version_number)
        )
        .scalars()
        .first()
    )
    if not pv:
        raise HTTPException(status_code=404, detail="Plan version not found")

    assignments = (
        db.execute(select(PlanAssignment).where(PlanAssignment.plan_version_id == pv.id))
        .scalars()
        .all()
    )

    tasks_by_id = {t.id: t for t in db.execute(select(Task)).scalars().all()}
    assets = db.execute(select(Asset).order_by(Asset.identifier.asc())).scalars().all()
    personnel = db.execute(select(Personnel).order_by(Personnel.name.asc())).scalars().all()
    maint_records = db.execute(select(MaintenanceRecord)).scalars().all()

    # Build Asset Tracks
    asset_tracks = []
    for a in assets:
        blocks = []
        # Task blocks
        for asgn in assignments:
            if asgn.asset_id == a.id:
                t = tasks_by_id.get(asgn.task_id)
                blocks.append({
                    "id": str(asgn.id),
                    "type": "task",
                    "code": t.code if t else "TASK",
                    "category": t.category if t else "sortie",
                    "priority": t.priority if t else "routine",
                    "start": asgn.assigned_start.isoformat(),
                    "end": asgn.assigned_end.isoformat(),
                    "duration_minutes": t.duration_minutes if t else 60,
                })
        # Maintenance blocks
        for m in maint_records:
            if m.asset_id == a.id:
                blocks.append({
                    "id": str(m.id),
                    "type": "maintenance",
                    "code": f"MAINT: {m.category}",
                    "category": m.category,
                    "priority": "critical",
                    "start": m.start_time.isoformat(),
                    "end": m.end_time.isoformat(),
                    "duration_minutes": int((m.end_time - m.start_time).total_seconds() / 60),
                })
        blocks.sort(key=lambda x: x["start"])
        asset_tracks.append({
            "asset_id": str(a.id),
            "identifier": a.identifier,
            "model_name": a.model_name,
            "asset_type": a.asset_type,
            "status": a.status,
            "blocks": blocks,
        })

    # Build Crew Tracks (Sample of active personnel)
    crew_tracks = []
    for p in personnel[:30]:  # Top 30 crew members for timeline performance
        blocks = []
        for asgn in assignments:
            if asgn.personnel_ids and p.id in asgn.personnel_ids:
                t = tasks_by_id.get(asgn.task_id)
                blocks.append({
                    "id": str(asgn.id),
                    "type": "sortie",
                    "code": t.code if t else "SORTIE",
                    "category": t.category if t else "sortie",
                    "start": asgn.assigned_start.isoformat(),
                    "end": asgn.assigned_end.isoformat(),
                })
        blocks.sort(key=lambda x: x["start"])
        crew_tracks.append({
            "personnel_id": str(p.id),
            "name": p.name,
            "callsign": p.callsign,
            "role_type": p.role_type,
            "blocks": blocks,
        })

    return {
        "plan_id": str(pv.plan_id),
        "version_number": pv.version_number,
        "as_of": pv.as_of.isoformat(),
        "asset_tracks": asset_tracks,
        "crew_tracks": crew_tracks,
    }


@router.get("/optimisation/weight-sets")
def get_weight_sets(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission([UserRole.PLANNER, UserRole.REVIEWER, UserRole.ANALYST, UserRole.ADMIN])),
) -> list[dict[str, Any]]:
    """Returns all versioned multi-objective penalty weight configurations."""
    weight_sets = db.execute(select(ObjectiveWeightSet).order_by(ObjectiveWeightSet.version.desc())).scalars().all()
    return [
        {
            "id": str(w.id),
            "version": w.version,
            "name": w.name,
            "delay_weight": w.delay_weight,
            "completion_weight": w.completion_weight,
            "churn_weight": w.churn_weight,
            "balance_weight": w.balance_weight,
            "buffer_weight": w.buffer_weight,
            "is_active": w.is_active,
            "created_by": w.created_by,
            "created_at": w.created_at.isoformat(),
        }
        for w in weight_sets
    ]


@router.post("/optimisation/weight-sets", status_code=status.HTTP_201_CREATED)
def create_weight_set(
    req: WeightSetCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(UserRole.ADMIN)),
) -> dict[str, Any]:
    """Creates a new version of objective weights (Admin only, audited)."""
    max_v = db.execute(select(func.coalesce(func.max(ObjectiveWeightSet.version), 0))).scalar_one()
    new_v = max_v + 1

    ws = ObjectiveWeightSet(
        version=new_v,
        name=req.name,
        delay_weight=req.delay_weight,
        completion_weight=req.completion_weight,
        churn_weight=req.churn_weight,
        balance_weight=req.balance_weight,
        buffer_weight=req.buffer_weight,
        is_active=True,
        created_by=current_user.email,
    )
    db.add(ws)
    db.flush()

    write_audit_entry(
        db=db,
        actor_id=current_user.id,
        role=current_user.roles[0].name if current_user.roles else "admin",
        action="CREATE_WEIGHT_SET",
        entity_type="objective_weight_sets",
        entity_id=str(ws.id),
        reason=f"Admin created objective weight set version {new_v}",
        after_state={"version": new_v, "name": req.name, "delay_weight": req.delay_weight, "completion_weight": req.completion_weight},
    )
    db.commit()

    return {
        "id": str(ws.id),
        "version": ws.version,
        "name": ws.name,
        "delay_weight": ws.delay_weight,
        "completion_weight": ws.completion_weight,
        "churn_weight": ws.churn_weight,
        "balance_weight": ws.balance_weight,
        "buffer_weight": ws.buffer_weight,
        "is_active": ws.is_active,
        "created_at": ws.created_at.isoformat(),
    }


@router.post("/optimisation/replan", status_code=status.HTTP_202_ACCEPTED)
def create_replan_job(
    req: ReplanJobRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission([UserRole.PLANNER, UserRole.ADMIN])),
) -> dict[str, Any]:
    """Triggers constrained replanning preserving frozen commitments and minimizing churn."""
    clock_as_of = req.as_of or get_clock().as_of()
    job_uuid = uuid.uuid4()
    job = Job(
        id=job_uuid,
        job_type="optimisation_replan",
        state=JobState.QUEUED.value,
        progress_percent=0.0,
        message=f"Queued replanning job: {req.disruption_reason} (frozen_window={req.frozen_window_minutes}m, limit={req.time_limit_seconds}s)",
    )
    db.add(job)
    db.commit()

    params = {
        "plan_id": str(req.plan_id) if req.plan_id else None,
        "frozen_window_minutes": req.frozen_window_minutes,
        "disruption_reason": req.disruption_reason,
        "time_limit_seconds": req.time_limit_seconds,
        "seed": req.seed,
        "weight_set_version": req.weight_set_version,
        "as_of": clock_as_of.isoformat(),
    }

    if req.run_async:
        run_replan_job.delay(str(job_uuid), params)
        return {
            "job_id": str(job_uuid),
            "job_type": "replan",
            "state": JobState.QUEUED.value,
            "message": "Replan job queued for asynchronous background execution via Celery",
        }
    else:
        from app.services.replanning import ReplanningService
        service = ReplanningService(db)
        result = service.execute_replan(
            job_id_str=str(job_uuid),
            plan_id=req.plan_id,
            frozen_window_minutes=req.frozen_window_minutes,
            disruption_reason=req.disruption_reason,
            time_limit_seconds=req.time_limit_seconds,
            seed=req.seed,
            weight_set_version=req.weight_set_version,
            as_of=clock_as_of,
        )
        return {
            "job_id": str(job_uuid),
            "job_type": "replan",
            "state": JobState.COMPLETED.value,
            "result": result,
        }


@router.post("/optimisation/rolling-horizon")
def trigger_rolling_horizon(
    req: RollingHorizonRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission([UserRole.PLANNER, UserRole.ADMIN])),
) -> dict[str, Any]:
    """Advances operational clock and runs rolling-horizon replanning cycle."""
    from app.services.clock import update_system_clock
    new_clock_state = update_system_clock(
        db=db,
        mode=ClockMode.SIMULATED,
        advance_seconds=float(req.advance_minutes * 60),
    )
    new_as_of = new_clock_state.current_as_of

    job_uuid = uuid.uuid4()
    job = Job(
        id=job_uuid,
        job_type="optimisation_rolling_horizon",
        state=JobState.QUEUED.value,
        progress_percent=0.0,
        message=f"Rolling horizon advanced by {req.advance_minutes}m to {new_as_of.isoformat()}",
    )
    db.add(job)
    db.commit()

    params = {
        "plan_id": str(req.plan_id) if req.plan_id else None,
        "frozen_window_minutes": req.frozen_window_minutes,
        "disruption_reason": f"Rolling horizon advance (+{req.advance_minutes}m)",
        "time_limit_seconds": req.time_limit_seconds,
        "seed": req.seed,
        "weight_set_version": req.weight_set_version,
        "as_of": new_as_of.isoformat(),
    }

    if req.run_async:
        run_replan_job.delay(str(job_uuid), params)
        return {
            "job_id": str(job_uuid),
            "new_as_of": new_as_of.isoformat(),
            "advance_minutes": req.advance_minutes,
            "state": JobState.QUEUED.value,
            "message": "Rolling horizon advance queued for asynchronous replanning",
        }
    else:
        from app.services.replanning import ReplanningService
        service = ReplanningService(db)
        result = service.execute_replan(
            job_id_str=str(job_uuid),
            plan_id=req.plan_id,
            frozen_window_minutes=req.frozen_window_minutes,
            disruption_reason=f"Rolling horizon advance (+{req.advance_minutes}m)",
            time_limit_seconds=req.time_limit_seconds,
            seed=req.seed,
            weight_set_version=req.weight_set_version,
            as_of=new_as_of,
        )
        return {
            "job_id": str(job_uuid),
            "new_as_of": new_as_of.isoformat(),
            "advance_minutes": req.advance_minutes,
            "state": JobState.COMPLETED.value,
            "result": result,
        }

