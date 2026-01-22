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
