"""
Health check endpoints
"""
from fastapi import APIRouter, Response
from datetime import datetime
import logging

from app.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "ok"
    }


@router.get("/health/ready")
async def readiness_check():
    """
    Readiness check - verifies all dependencies are available
    """
    checks = {
        "acs_configured": bool(settings.ACS_CONNECTION_STRING),
        "storage_configured": bool(settings.AZURE_STORAGE_CONNECTION_STRING),
        "database_configured": bool(settings.DATABASE_URL),
    }
    
    all_ready = all(checks.values())
    
    return Response(
        content=str({
            "ready": all_ready,
            "checks": checks,
            "timestamp": datetime.utcnow().isoformat()
        }),
        status_code=200 if all_ready else 503,
        media_type="application/json"
    )


@router.get("/health/live")
async def liveness_check():
    """Liveness check - simple ping to verify service is running"""
    return {"alive": True}
