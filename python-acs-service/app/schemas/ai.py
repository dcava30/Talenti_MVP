"""AI interviewer schemas."""
from typing import Optional

from pydantic import BaseModel, Field


class AiInterviewerRequest(BaseModel):
    """Payload for starting an AI interviewer."""

    interview_id: int
    prompt: Optional[str] = Field(default=None, max_length=500)


class AiInterviewerResponse(BaseModel):
    """Response for AI interviewer initiation."""

    status: str
    interview_id: int
    message: str
