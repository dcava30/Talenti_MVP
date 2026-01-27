"""
API router configuration for the ACS service.
"""
from fastapi import APIRouter

from app.api.routes import (
    health,
    calls,
    recordings,
    auth,
    organisations,
    roles,
    candidates,
    interviews,
    invitations,
    scoring,
    resume,
    shortlist,
    requirements,
    acs,
    speech,
    webhooks,
)

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(calls.router, prefix="/api/calls", tags=["Calls"])
api_router.include_router(recordings.router, prefix="/api/recordings", tags=["Recordings"])
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(organisations.router, prefix="/organisations", tags=["Organisations"])
api_router.include_router(roles.router, prefix="/roles", tags=["Roles"])
api_router.include_router(candidates.router, prefix="/candidates", tags=["Candidates"])
api_router.include_router(interviews.router, prefix="/interviews", tags=["Interviews"])
api_router.include_router(interviews.ai_router, prefix="/ai", tags=["AI"])
api_router.include_router(invitations.router, prefix="/invitations", tags=["Invitations"])
api_router.include_router(scoring.router, prefix="/scoring", tags=["Scoring"])
api_router.include_router(resume.router, prefix="/resume", tags=["Resume"])
api_router.include_router(shortlist.router, prefix="/shortlist", tags=["Shortlist"])
api_router.include_router(requirements.router, prefix="/requirements", tags=["Requirements"])
api_router.include_router(acs.router, prefix="/acs", tags=["ACS"])
api_router.include_router(speech.router, prefix="/speech", tags=["Speech"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
