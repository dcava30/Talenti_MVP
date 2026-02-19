"""Requirements extraction endpoints."""
from fastapi import APIRouter, Depends

from app.schemas.requirements import RequirementsExtractRequest, RequirementsExtractResponse
from app.security.dependencies import get_current_user
from app.models.user import User

router = APIRouter()


@router.post("/extract", response_model=RequirementsExtractResponse)
def extract_requirements(
    payload: RequirementsExtractRequest,
    user: User = Depends(get_current_user),
) -> RequirementsExtractResponse:
    """Extract requirements from a role description."""
    lines = [line.strip(" -") for line in payload.description.splitlines() if line.strip()]
    requirements = lines[:5] if lines else ["Requirement extraction pending"]
    return RequirementsExtractResponse(requirements=requirements)
