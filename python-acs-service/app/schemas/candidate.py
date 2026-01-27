"""Candidate schemas."""
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CandidateCreate(BaseModel):
    """Payload for creating a candidate."""

    full_name: Optional[str] = Field(None, max_length=255)
    email: Optional[str] = None


class CandidateResponse(BaseModel):
    """Candidate response payload."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    organisation_id: int
    full_name: Optional[str] = None
    email: Optional[str] = None
