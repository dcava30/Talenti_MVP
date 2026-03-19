from contextlib import asynccontextmanager
import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    acs,
    ai,
    applications,
    audit_log,
    auth,
    call_automation,
    candidates,
    interview_scores,
    interviews,
    invitations,
    orgs,
    requirements,
    resume_batches,
    retention,
    roles,
    scoring,
    shortlist,
    speech,
    storage,
)
from app.core.config import settings
from app.core.logging import configure_logging, log_context
from app.core.migrations import run_startup_migrations

configure_logging(service_name="backend-api", log_level=settings.log_level, disable_uvicorn_access=True)
logger = logging.getLogger("backend-api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Talenti API", extra={"event": "startup"})
    run_startup_migrations()
    yield
    logger.info("Stopping Talenti API", extra={"event": "shutdown"})


app = FastAPI(title="Talenti API", lifespan=lifespan)
if settings.allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
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
                "Unhandled request error",
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
            "Completed request",
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


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(ai.router)
app.include_router(acs.router)
app.include_router(call_automation.router)
app.include_router(speech.router)
app.include_router(orgs.router)
app.include_router(roles.router)
app.include_router(candidates.router)
app.include_router(resume_batches.router)
app.include_router(requirements.router)
app.include_router(scoring.router)
app.include_router(shortlist.router)
app.include_router(retention.router)
app.include_router(applications.router)
app.include_router(audit_log.router)
app.include_router(invitations.router)
app.include_router(invitations.v1_router)
app.include_router(interviews.router)
app.include_router(interview_scores.router)
app.include_router(storage.router)
