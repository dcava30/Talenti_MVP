"""Role schemas."""
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class RoleCreate(BaseModel):
    """Payload for creating a role."""

    name: str = Field(..., min_length=1, max_length=255)
    organisation_id: Optional[int] = None


class RoleUpdate(BaseModel):
    """Payload for updating a role."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)


class RoleResponse(BaseModel):
    """Role response payload."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    organisation_id: int
