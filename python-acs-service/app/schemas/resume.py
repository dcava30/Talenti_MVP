"""Resume parsing schemas."""
from typing import List, Optional

from pydantic import BaseModel, Field


class ResumeParseRequest(BaseModel):
    """Payload for resume parsing."""

    content: str = Field(..., min_length=1)
    filename: Optional[str] = Field(default=None, max_length=255)


class ResumeParseResponse(BaseModel):
    """Response for parsed resume."""

    summary: str
    skills: List[str]
