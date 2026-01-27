"""Shortlist generation schemas."""
from typing import List, Optional

from pydantic import BaseModel, Field


class ShortlistGenerateRequest(BaseModel):
    """Payload for generating a shortlist."""

    role_id: Optional[int] = None
    candidate_ids: List[int]


class ShortlistGenerateResponse(BaseModel):
    """Response for shortlist generation."""

    shortlist: List[int]
    message: str = Field(default="Shortlist generated")
