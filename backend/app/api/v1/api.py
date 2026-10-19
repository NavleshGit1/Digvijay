from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.demo import router as demo_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.overview import router as overview_router
from app.api.v1.stream import router as stream_router
from app.api.v1.system import router as system_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth_router)
api_router.include_router(system_router)
api_router.include_router(jobs_router)
api_router.include_router(stream_router)
api_router.include_router(overview_router)
api_router.include_router(demo_router)
