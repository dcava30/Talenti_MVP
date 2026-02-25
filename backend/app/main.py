from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    acs,
    ai,
    applications,
    audit_log,
    auth,
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


app = FastAPI(title="Talenti API")
if settings.allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.on_event("startup")
def on_startup() -> None:
    alembic_config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    alembic_config.set_main_option("sqlalchemy.url", settings.database_url)
    command.upgrade(alembic_config, "head")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(ai.router)
app.include_router(acs.router)
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
