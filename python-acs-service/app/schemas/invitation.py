"""Invitation schemas."""
from typing import Optional

from pydantic import BaseModel, Field


class InvitationSendRequest(BaseModel):
    """Payload for sending an interview invitation."""

    email: str
    role_id: Optional[int] = None
    candidate_name: Optional[str] = Field(None, max_length=255)
    message: Optional[str] = Field(None, max_length=500)


class InvitationSendResponse(BaseModel):
    """Response for sending an invitation."""

    status: str
    email: str
