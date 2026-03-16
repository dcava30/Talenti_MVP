from datetime import datetime
from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    full_name: str | None
    password_setup_required: bool = False
    invited_via_org: bool = False
    account_claimed_at: datetime | None = None
    created_at: datetime


class ClaimInviteRequest(BaseModel):
    token: str
    email: EmailStr
    password: str
    full_name: str | None = None


class ClaimInviteContextResponse(BaseModel):
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
