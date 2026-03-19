"""
Talenti ACS Service - FastAPI Application
Handles Azure Communication Services call automation and recording
"""
from contextlib import asynccontextmanager
import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.router import api_router
from app.logging_utils import configure_logging, log_context

configure_logging(
    service_name="acs-worker",
    log_level=settings.LOG_LEVEL,
    disable_uvicorn_access=True,
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting Talenti ACS Service", extra={"event": "startup"})
    logger.info("Loaded ACS configuration", extra={"event": "config_loaded", "acs_endpoint": settings.ACS_ENDPOINT})
    if settings.ENVIRONMENT.lower() == "production" and not settings.ACS_WORKER_SHARED_SECRET:
        raise RuntimeError("ACS_WORKER_SHARED_SECRET must be set in production environments.")
    yield
    logger.info("Shutting down Talenti ACS Service", extra={"event": "shutdown"})


app = FastAPI(
    title="Talenti ACS Service",
    description="Azure Communication Services integration for AI interviews",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
cors_origins = [settings.FRONTEND_ORIGIN] if settings.FRONTEND_ORIGIN else settings.ALLOWED_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    start = time.perf_counter()

    with log_context(request_id=request_id):
        try:
            response = await call_next(request)
        except Exception:  # noqa: BLE001
            route_path = getattr(request.scope.get("route"), "path", request.url.path)
            logger.exception(
                "Unhandled ACS request error",
                extra={
                    "event": "http_request",
                    "method": request.method,
                    "path": request.url.path,
                    "route": route_path,
                    "status_code": 500,
                    "duration_ms": round((time.perf_counter() - start) * 1000, 2),
                },
            )
            raise

        route_path = getattr(request.scope.get("route"), "path", request.url.path)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "Completed ACS request",
            extra={
                "event": "http_request",
                "method": request.method,
                "path": request.url.path,
                "route": route_path,
                "status_code": response.status_code,
                "duration_ms": round((time.perf_counter() - start) * 1000, 2),
            },
        )
        return response


# Include routers
app.include_router(api_router)


@app.get("/")
async def root():
    return {
        "service": "Talenti ACS Service",
        "version": "1.0.0",
        "status": "running"
    }
