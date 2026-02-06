from datetime import datetime
from pydantic import BaseModel, EmailStr


class InvitationCreate(BaseModel):
    application_id: str
    candidate_email: EmailStr
    expires_at: datetime
    email_template: str | None = None


class InvitationResponse(BaseModel):
    id: str
    application_id: str
    token: str
    status: str
    expires_at: datetime
    created_at: datetime


class InvitationUpdate(BaseModel):
    status: str | None = None


class InvitationValidationResponse(BaseModel):
    valid: bool
    invitation: dict | None = None
    application: dict | None = None
    jobRole: dict | None = None
