import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.exceptions import AppException, problem_exception_handler
from app.core.logging import setup_logging
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.services.auth import seed_demo_users
from app.services.clock import init_system_clock

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown lifecycle manager."""
    setup_logging(debug=settings.DEBUG)
    logger.info("Initializing AirOps Nexus platform skeleton", environment=settings.ENVIRONMENT)

    # Initialize tables
    Base.metadata.create_all(bind=engine)

    # Seed initial demo data and clock state
    db = SessionLocal()
    try:
        seed_demo_users(db)
        init_system_clock(db)
        logger.info("Demo users and virtual clock state successfully initialized")
    finally:
        db.close()

    yield

    logger.info("AirOps Nexus platform shutting down gracefully")


def create_app() -> FastAPI:
    """Application factory for AirOps Nexus FastAPI backend."""
    app = FastAPI(
        title="AirOps Nexus API",
        version="0.1.0",
        description="Air Power: Dynamic Air Operations and Resource Optimisation (Synthetic Prototype)",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request ID and structured logging middleware
    @app.middleware("http")
    async def request_id_logging_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id, path=request.url.path)

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    # Exception Handlers (RFC 7807)
    app.add_exception_handler(AppException, problem_exception_handler)

    # Mount API routers
    app.include_router(api_router)

    @app.websocket("/ws")
    async def top_level_websocket(websocket: WebSocket) -> None:
        from app.api.v1.stream import websocket_stream_handler
        await websocket_stream_handler(websocket)

    @app.get("/")
    def root():
        return {
            "name": "AirOps Nexus API",
            "version": "0.1.0",
            "status": "online",
            "docs": "/docs",
            "ws": "/ws",
            "synthetic_prototype": True,
        }

    return app


app = create_app()
