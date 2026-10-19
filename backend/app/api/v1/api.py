from fastapi import APIRouter

from app.api.v1.admin import router as admin_router
from app.api.v1.auth import router as auth_router
from app.api.v1.demo import router as demo_router
from app.api.v1.events import router as events_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.overview import router as overview_router
from app.api.v1.resources import router as resources_router
from app.api.v1.search import router as search_router
from app.api.v1.stream import router as stream_router
from app.api.v1.system import router as system_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth_router)
api_router.include_router(admin_router)
api_router.include_router(system_router)
api_router.include_router(jobs_router)
api_router.include_router(stream_router)
api_router.include_router(overview_router)
api_router.include_router(demo_router)
api_router.include_router(resources_router)
api_router.include_router(search_router)
api_router.include_router(events_router)

