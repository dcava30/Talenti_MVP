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
    candidate_email: EmailStr | None = None
    claim_required: bool = False
    profile_completion_required: bool = False
    invitation_kind: str | None = None
    expires_at: datetime
    created_at: datetime


class InvitationUpdate(BaseModel):
    status: str | None = None


class InvitationValidationResponse(BaseModel):
    valid: bool
    invitation: dict | None = None
    application: dict | None = None
    jobRole: dict | None = None
    candidate_email: EmailStr | None = None
    claim_required: bool = False
    profile_completion_required: bool = False
    account_claimed: bool = False
    profile_confirmed: bool = False
    interview_unlocked: bool = False
