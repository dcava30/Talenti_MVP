from contextlib import asynccontextmanager

from fastapi import FastAPI
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
    retention,
    roles,
    scoring,
    shortlist,
    speech,
    storage,
)
from app.core.config import settings
from app.core.migrations import run_startup_migrations


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_startup_migrations()
    yield


app = FastAPI(title="Talenti API", lifespan=lifespan)
if settings.allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

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
