"""Organisation schemas."""
from pydantic import BaseModel, ConfigDict, Field


class OrganisationCreate(BaseModel):
    """Payload for creating an organisation."""

    name: str = Field(..., min_length=1, max_length=255)


class OrganisationResponse(BaseModel):
    """Organisation response payload."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
