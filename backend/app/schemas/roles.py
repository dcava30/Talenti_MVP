from datetime import datetime
from pydantic import BaseModel


class JobRoleCreate(BaseModel):
    organisation_id: str
    title: str
    description: str | None = None
    department: str | None = None
    location: str | None = None
    work_type: str | None = None
    employment_type: str | None = None


class JobRoleResponse(BaseModel):
    id: str
    organisation_id: str
    title: str
    status: str
    created_at: datetime


class JobRoleDetail(BaseModel):
    id: str
    organisation_id: str
    title: str
    description: str | None
    department: str | None
    location: str | None
    work_type: str | None
    employment_type: str | None
    industry: str | None
    requirements: str | None
    scoring_rubric: str | None
    interview_structure: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class JobRoleUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    department: str | None = None
    location: str | None = None
    work_type: str | None = None
    employment_type: str | None = None
    industry: str | None = None
    requirements: str | None = None
    interview_structure: str | None = None
    status: str | None = None


class JobRoleRubricUpdate(BaseModel):
    scoring_rubric: str
