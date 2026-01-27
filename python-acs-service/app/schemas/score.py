"""Interview scoring schemas."""
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ScoreCreate(BaseModel):
    """Payload for creating a score."""

    interview_id: int
    score: Optional[float] = Field(None, ge=0, le=100)
    summary: Optional[str] = None


class ScoreResponse(BaseModel):
    """Score response payload."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    interview_id: int
    score: Optional[float] = None
    summary: Optional[str] = None
