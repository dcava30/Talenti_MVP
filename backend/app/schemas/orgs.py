from datetime import datetime
from pydantic import BaseModel


class OrganisationCreate(BaseModel):
    name: str
    description: str | None = None
    industry: str | None = None
    website: str | None = None


class OrganisationResponse(BaseModel):
    id: str
    name: str
    description: str | None
    industry: str | None
    website: str | None
    created_at: datetime
