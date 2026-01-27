"""Requirement extraction schemas."""
from typing import List

from pydantic import BaseModel, Field


class RequirementsExtractRequest(BaseModel):
    """Payload for extracting requirements."""

    description: str = Field(..., min_length=1)


class RequirementsExtractResponse(BaseModel):
    """Response for extracted requirements."""

    requirements: List[str]
