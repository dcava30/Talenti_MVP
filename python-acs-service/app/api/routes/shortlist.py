"""Shortlist generation endpoints."""
from fastapi import APIRouter, Depends

from app.schemas.shortlist import ShortlistGenerateRequest, ShortlistGenerateResponse
from app.security.dependencies import get_current_user
from app.models.user import User

router = APIRouter()


@router.post("/generate", response_model=ShortlistGenerateResponse)
def generate_shortlist(
    payload: ShortlistGenerateRequest,
    user: User = Depends(get_current_user),
) -> ShortlistGenerateResponse:
    """Generate a shortlist from candidate identifiers."""
    shortlist = sorted(payload.candidate_ids)
    return ShortlistGenerateResponse(shortlist=shortlist, message="Shortlist generated")
