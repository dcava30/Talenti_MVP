from datetime import datetime
from typing import Any
from pydantic import BaseModel


class OrganisationCreate(BaseModel):
    name: str
    description: str | None = None
    industry: str | None = None
    website: str | None = None
    values_framework: dict[str, Any] | str | None = None


class OrganisationResponse(BaseModel):
    id: str
    name: str
    description: str | None
    industry: str | None
    website: str | None
    created_at: datetime


class OrganisationDetail(BaseModel):
    id: str
    name: str
    description: str | None
    industry: str | None
    website: str | None
    values_framework: str | None
    recording_retention_days: int | None
    created_at: datetime
    updated_at: datetime


class OrgMembershipResponse(BaseModel):
    id: str
    role: str
    organisation: OrganisationDetail


class OrgRetentionUpdate(BaseModel):
    recording_retention_days: int


class OrgStatsResponse(BaseModel):
    activeRoles: int
    totalCandidates: int
    completedInterviews: int
    avgMatchScore: int | None
