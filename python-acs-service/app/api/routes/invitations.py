"""Invitation endpoints."""
from fastapi import APIRouter, Depends

from app.schemas.invitation import InvitationSendRequest, InvitationSendResponse
from app.security.dependencies import get_current_user
from app.models.user import User

router = APIRouter()


@router.post("/send", response_model=InvitationSendResponse)
def send_invitation(
    payload: InvitationSendRequest,
    user: User = Depends(get_current_user),
) -> InvitationSendResponse:
    """Send an interview invitation (stub)."""
    return InvitationSendResponse(status="queued", email=payload.email)
