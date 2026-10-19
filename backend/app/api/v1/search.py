from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.logistics import Part
from app.models.operations import Task
from app.models.resources import Asset, Personnel
from app.schemas.search import SearchResponse, SearchResultItem

router = APIRouter(tags=["search"])


@router.get("/search", response_model=SearchResponse)
def search_entities(
    q: str = Query(..., min_length=1, description="Search term across all entities"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> SearchResponse:
    """Unified search across Assets, Personnel, Tasks, and Spares Catalog."""
    search_term = f"%{q.strip()}%"
    results: list[SearchResultItem] = []

    # 1. Search Assets
    asset_stmt = (
        select(Asset)
        .where(
            or_(
                Asset.identifier.ilike(search_term),
                Asset.model_name.ilike(search_term),
                Asset.asset_type.ilike(search_term),
            )
        )
        .limit(limit)
    )
    for a in db.execute(asset_stmt).scalars().all():
        results.append(
            SearchResultItem(
                category="asset",
                id=str(a.id),
                title=f"{a.identifier} ({a.model_name})",
                subtitle=f"Type: {a.asset_type} | Health: {round(a.health_score * 100, 1)}%",
                badge=a.status.upper(),
                url=f"/assets?search={a.identifier}",
            )
        )

    # 2. Search Personnel
    personnel_stmt = (
        select(Personnel)
        .where(
            or_(
                Personnel.name.ilike(search_term),
                Personnel.callsign.ilike(search_term),
                Personnel.role_type.ilike(search_term),
            )
        )
        .limit(limit)
    )
    for p in db.execute(personnel_stmt).scalars().all():
        callsign_str = f" '{p.callsign}'" if p.callsign else ""
        results.append(
            SearchResultItem(
                category="personnel",
                id=str(p.id),
                title=f"{p.name}{callsign_str}",
                subtitle=f"Role: {p.role_type.replace('_', ' ').title()} | Duty: {round(p.duty_hours_accumulated, 1)}h",
                badge=p.status.upper(),
                url=f"/personnel?search={p.name}",
            )
        )

    # 3. Search Tasks
    task_stmt = (
        select(Task)
        .where(
            or_(
                Task.code.ilike(search_term),
                Task.category.ilike(search_term),
            )
        )
        .limit(limit)
    )
    for t in db.execute(task_stmt).scalars().all():
        results.append(
            SearchResultItem(
                category="task",
                id=str(t.id),
                title=f"Task {t.code}",
                subtitle=f"Category: {t.category.replace('_', ' ').title()} | {t.duration_minutes}m",
                badge=t.priority.upper(),
                url=f"/operations?search={t.code}",
            )
        )

    # 4. Search Parts Catalog
    part_stmt = (
        select(Part)
        .where(
            or_(
                Part.part_number.ilike(search_term),
                Part.name.ilike(search_term),
                Part.category.ilike(search_term),
            )
        )
        .limit(limit)
    )
    for part in db.execute(part_stmt).scalars().all():
        results.append(
            SearchResultItem(
                category="spare",
                id=str(part.id),
                title=f"{part.part_number} - {part.name}",
                subtitle=f"Category: {part.category.title()} | Unit: ${part.unit_cost:.2f}",
                badge="PART",
                url=f"/maintenance?tab=spares&search={part.part_number}",
            )
        )

    # Slice to total limit requested
    final_results = results[:limit]
    return SearchResponse(
        query=q,
        total=len(final_results),
        results=final_results,
    )
