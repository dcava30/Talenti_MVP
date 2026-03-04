"""
API router configuration for the ACS service.
"""
from fastapi import APIRouter, Depends

from app.api.routes import (
    health,
    calls,
    recordings,
)
from app.security.internal import require_internal_shared_secret

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(
    calls.router,
    prefix="/internal/calls",
    tags=["Calls"],
    dependencies=[Depends(require_internal_shared_secret)],
)
api_router.include_router(
    recordings.router,
    prefix="/internal/recordings",
    tags=["Recordings"],
    dependencies=[Depends(require_internal_shared_secret)],
)
