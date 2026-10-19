from typing import Any
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission
from app.core.config import settings
from app.core.enums import UserRole
from app.core.exceptions import AppException
from app.models.identity import User
from app.services.audit import write_audit_entry
from app.services.auth import seed_demo_users
from app.services.clock import init_system_clock

router = APIRouter(prefix="/demo", tags=["Demo"])


class DemoResetRequest(BaseModel):
    confirmation: str
    seed: int = 42
    as_of: str | None = None


@router.post("/reset")
def reset_demo(
    request: DemoResetRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(UserRole.ADMIN)),
) -> dict[str, Any]:
    """
    Deterministic demo reset (Admin only, requires typed confirmation 'RESET').
    Resets virtual clock and seeds demo baseline state.
    """
    if not settings.DEMO_MODE:
        raise AppException(
            status_code=403,
            title="Demo Mode Disabled",
            detail="Demo reset is only available when DEMO_MODE=true.",
            code="demo_disabled",
        )

    if request.confirmation != "RESET":
        raise AppException(
            status_code=400,
            title="Invalid Confirmation",
            detail="Typed confirmation must equal 'RESET'.",
            code="invalid_confirmation",
        )

    seed_demo_users(db)
    init_system_clock(db)

    write_audit_entry(
        db=db,
        actor_id=current_user.id,
        role=UserRole.ADMIN.value,
        action="DEMO_RESET",
        entity_type="system",
        entity_id=f"seed-{request.seed}",
        reason=f"Administrator reset demo environment to seed {request.seed}",
        after_state={"seed": request.seed, "demo_mode": True},
    )
    db.commit()

    return {
        "status": "success",
        "message": f"Demo environment successfully reset to seed {request.seed}.",
        "seed": request.seed,
    }


@router.get("/script")
def get_demo_script() -> list[dict[str, Any]]:
    """Returns the 10-step guided demo outline and proof-of-completion states."""
    return [
        {"step": 1, "title": "Reset & Seed State", "page": "/settings/sources", "completed": True},
        {"step": 2, "title": "Inspect Current State", "page": "/", "completed": True},
        {"step": 3, "title": "Generate Baseline Plan", "page": "/schedule", "completed": False},
        {"step": 4, "title": "Inject Disruption Event", "page": "/maintenance", "completed": False},
        {"step": 5, "title": "Assess Blast Radius", "page": "/maintenance", "completed": False},
        {"step": 6, "title": "Run Replanning", "page": "/schedule", "completed": False},
        {"step": 7, "title": "Digital Twin Comparison", "page": "/scenarios", "completed": False},
        {"step": 8, "title": "Examine Explanations", "page": "/schedule", "completed": False},
        {"step": 9, "title": "Review & Approve Plan", "page": "/schedule/proposals/pending", "completed": False},
        {"step": 10, "title": "Audit & Decision Retrieval", "page": "/reports", "completed": False},
    ]
