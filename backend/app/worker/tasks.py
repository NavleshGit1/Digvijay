import json
import time
import uuid
from sqlalchemy import select

from app.core.enums import JobState
from app.core.locks import redis_client
from app.db.session import SessionLocal
from app.models.jobs import Job
from app.services.audit import write_audit_entry
from app.worker.celery_app import celery_app


def publish_job_progress(job_id: str, state: str, progress: float, message: str) -> None:
    """Publishes job progress over Redis pub/sub for live SSE delivery."""
    payload = json.dumps({
        "job_id": job_id,
        "state": state,
        "progress_percent": progress,
        "message": message,
    })
    try:
        redis_client.publish("jobs:progress", payload)
        redis_client.set(f"job:{job_id}:state", payload, ex=3600)
    except Exception:
        pass


@celery_app.task(bind=True, queue="default")
def dummy_job(self, job_id_str: str, duration_seconds: int = 5) -> dict:
    """
    Demonstration task streaming progress over Redis/SSE and recording final state in Postgres.
    Validates Phase 1 Exit Gate: 'a dummy job reports queued, running, and completed over SSE;
    its audit record exists and cannot be altered.'
    """
    job_uuid = uuid.UUID(job_id_str)
    db = SessionLocal()

    try:
        # Mark as RUNNING
        stmt = select(Job).where(Job.id == job_uuid)
        job = db.execute(stmt).scalars().first()
        if job:
            job.state = JobState.RUNNING.value
            job.progress_percent = 5.0
            job.message = "Job initialized, commencing simulation"
            db.commit()

        publish_job_progress(job_id_str, JobState.RUNNING.value, 5.0, "Job initialized")

        # Step through progress
        steps = 5
        sleep_interval = duration_seconds / steps

        for step in range(1, steps + 1):
            time.sleep(sleep_interval)
            pct = (step / steps) * 100.0
            msg = f"Executing processing phase {step} of {steps}"

            if job:
                job.progress_percent = pct
                job.message = msg
                db.commit()

            publish_job_progress(job_id_str, JobState.RUNNING.value, pct, msg)

        # Mark COMPLETED
        if job:
            job.state = JobState.COMPLETED.value
            job.progress_percent = 100.0
            job.message = "Execution completed successfully"
            job.result_id = f"RESULT-{job_id_str[:8]}"
            db.commit()

        publish_job_progress(job_id_str, JobState.COMPLETED.value, 100.0, "Execution completed successfully")

        # Write audit log entry
        write_audit_entry(
            db=db,
            actor_id=None,
            role="system",
            action="EXECUTE_JOB",
            entity_type="jobs",
            entity_id=job_id_str,
            reason="Dummy async demonstration job completed",
            after_state={"state": JobState.COMPLETED.value, "result_id": f"RESULT-{job_id_str[:8]}"},
        )
        db.commit()

        return {"job_id": job_id_str, "status": "completed"}

    except Exception as e:
        if job:
            job.state = JobState.FAILED.value
            job.message = str(e)
            db.commit()
        publish_job_progress(job_id_str, JobState.FAILED.value, 0.0, f"Error: {e}")
        raise
    finally:
        db.close()


@celery_app.task(bind=True, queue="optimise")
def run_optimisation_job(self, job_id_str: str, params: dict | None = None) -> dict:
    """Celery task executing Baseline or CP-SAT optimisation job with SSE progress streaming."""
    from app.services.optimisation import OptimisationService

    params = params or {}
    db = SessionLocal()
    try:
        def progress_callback(pct: float, msg: str):
            publish_job_progress(job_id_str, JobState.RUNNING.value, pct, msg)

        service = OptimisationService(db)
        result = service.execute_optimisation_job(
            job_id_str=job_id_str,
            job_type=params.get("job_type", "optimise"),
            plan_name=params.get("plan_name", "Operational Master Plan 2026"),
            time_limit_seconds=float(params.get("time_limit_seconds", 15.0)),
            seed=int(params.get("seed", 42)),
            weight_set_version=int(params.get("weight_set_version", 1)),
            progress_cb=progress_callback,
        )
        publish_job_progress(job_id_str, JobState.COMPLETED.value, 100.0, "Optimisation execution completed successfully")
        return result
    except Exception as e:
        job_uuid = uuid.UUID(job_id_str)
        job = db.execute(select(Job).where(Job.id == job_uuid)).scalars().first()
        if job:
            job.state = JobState.FAILED.value
            job.message = str(e)
            db.commit()
        publish_job_progress(job_id_str, JobState.FAILED.value, 0.0, f"Optimisation job failed: {e}")
        raise
    finally:
        db.close()


@celery_app.task(bind=True, queue="optimise")
def run_replan_job(self, job_id_str: str, params: dict | None = None) -> dict:
    """Celery task executing controlled replanning with frozen window and churn penalty."""
    from app.services.replanning import ReplanningService

    params = params or {}
    db = SessionLocal()
    try:
        def progress_callback(pct: float, msg: str):
            publish_job_progress(job_id_str, JobState.RUNNING.value, pct, msg)

        service = ReplanningService(db)
        plan_id = uuid.UUID(params["plan_id"]) if params.get("plan_id") else None
        result = service.execute_replan(
            job_id_str=job_id_str,
            plan_id=plan_id,
            frozen_window_minutes=int(params.get("frozen_window_minutes", 120)),
            disruption_reason=params.get("disruption_reason", "Operational disruption replan"),
            time_limit_seconds=float(params.get("time_limit_seconds", 15.0)),
            seed=int(params.get("seed", 42)),
            weight_set_version=int(params.get("weight_set_version", 1)),
            progress_cb=progress_callback,
        )
        publish_job_progress(job_id_str, JobState.COMPLETED.value, 100.0, "Replanning completed successfully")
        return result
    except Exception as e:
        job_uuid = uuid.UUID(job_id_str)
        job = db.execute(select(Job).where(Job.id == job_uuid)).scalars().first()
        if job:
            job.state = JobState.FAILED.value
            job.message = str(e)
            db.commit()
        publish_job_progress(job_id_str, JobState.FAILED.value, 0.0, f"Replan job failed: {e}")
        raise
    finally:
        db.close()


@celery_app.task(bind=True, queue="default")
def run_alert_evaluation_job(self) -> dict:
    """Periodic Celery Beat task evaluating system alert rules and anti-flapping deduplication."""
    from app.services.alerts import evaluate_system_alerts
    db = SessionLocal()
    try:
        return evaluate_system_alerts(db)
    finally:
        db.close()


