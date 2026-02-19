"""Interview schemas."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class InterviewCreate(BaseModel):
    """Payload for creating an interview."""

    candidate_id: int
    role_id: Optional[int] = None
    scheduled_at: Optional[datetime] = None
    notes: Optional[str] = None
    status: Optional[str] = Field(default="scheduled", max_length=100)


class InterviewResponse(BaseModel):
    """Interview response payload."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    organisation_id: int
    candidate_id: int
    role_id: Optional[int] = None
    status: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    notes: Optional[str] = None
    recording_started: bool
    recording_processed: bool
    recording_id: Optional[str] = None
    recording_url: Optional[str] = None


class InterviewEventCreate(BaseModel):
    """Payload for recording interview events."""

    event_type: str = Field(..., min_length=1, max_length=100)
    payload: Optional[dict] = None


class InterviewEventResponse(BaseModel):
    """Interview event response payload."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    interview_id: int
    event_type: str
    payload: Optional[dict] = None


class InterviewCompleteResponse(BaseModel):
    """Response for completing an interview."""

    id: int
    status: str
