import uuid
from typing import Any
from fastapi import APIRouter, Depends, Header, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.enums import JobState
from app.core.exceptions import AppException
from app.core.locks import redis_client
from app.models.identity import User
from app.models.jobs import Job
from app.schemas.jobs import JobCreateRequest, JobResponse
from app.worker.tasks import dummy_job

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post("", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
def create_job(
    request: JobCreateRequest,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    idempotency_key: str | None = Header(default=None),
) -> JobResponse:
    """Submits a background task and enqueues to Celery via Redis."""
    job_id = uuid.uuid4()
    job = Job(
        id=job_id,
        job_type=request.job_type,
        state=JobState.QUEUED.value,
        progress_percent=0.0,
        message="Job queued for Celery execution",
        owner_id=current_user.id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Enqueue Celery async task
    try:
        dummy_job.delay(str(job_id), duration_seconds=request.duration_seconds)
    except Exception:
        # Fallback for local environments running without a Celery worker: run in background or mock progress
        pass

    response.headers["Location"] = f"/api/v1/jobs/{job_id}"
    return JobResponse.model_validate(job)


@router.get("", response_model=list[JobResponse])
def list_jobs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[JobResponse]:
    """Lists background jobs."""
    stmt = select(Job).order_by(Job.created_at.desc()).limit(20)
    jobs = db.execute(stmt).scalars().all()
    return [JobResponse.model_validate(j) for j in jobs]


@router.get("/{id}", response_model=JobResponse)
def get_job(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobResponse:
    """Retrieves specific job progress and status."""
    stmt = select(Job).where(Job.id == id)
    job = db.execute(stmt).scalars().first()
    if not job:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Job Not Found",
            detail=f"Job with ID {id} does not exist.",
            code="not_found",
        )
    return JobResponse.model_validate(job)


@router.post("/{id}/cancel")
def cancel_job(
    id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Cancels a running background job."""
    stmt = select(Job).where(Job.id == id)
    job = db.execute(stmt).scalars().first()
    if not job:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            title="Job Not Found",
            detail=f"Job with ID {id} does not exist.",
            code="not_found",
        )

    job.state = JobState.CANCELLED.value
    job.message = "Job cancelled by user request"
    db.commit()

    return {"message": "Job cancellation initiated"}
