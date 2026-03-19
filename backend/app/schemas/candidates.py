from datetime import datetime

from pydantic import BaseModel, EmailStr


class ParseResumeRequest(BaseModel):
    candidate_id: str | None = None
    file_id: str | None = None
    resume_text: str | None = None


class ParsedResume(BaseModel):
    full_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    skills: list[str] = []
    linkedin_url: str | None = None
    portfolio_url: str | None = None
    summary: str | None = None
    employment: list[dict] = []
    education: list[dict] = []
    confidence: dict = {}


class ParseResumeResponse(BaseModel):
    candidate_id: str
    parsed: ParsedResume


class CandidateProfileBase(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    suburb: str | None = None
    state: str | None = None
    postcode: str | None = None
    country: str | None = None
    linkedin_url: str | None = None
    portfolio_url: str | None = None
    cv_file_id: str | None = None
    cv_file_path: str | None = None
    profile_prefilled: bool | None = None
    profile_confirmed_at: datetime | None = None
    profile_review_status: str | None = None
    prefill_source: str | None = None
    parsed_snapshot_id: str | None = None
    availability: str | None = None
    work_mode: str | None = None
    work_rights: str | None = None
    gpa_wam: float | None = None
    profile_visibility: str | None = None
    visibility_settings: str | None = None


class CandidateProfileCreate(CandidateProfileBase):
    user_id: str | None = None


class CandidateProfileResponse(CandidateProfileBase):
    id: str
    user_id: str
    paused_at: datetime | None
    created_at: datetime
    updated_at: datetime


class EmploymentCreate(BaseModel):
    user_id: str
    company: str
    title: str
    location: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    description: str | None = None


class EmploymentUpdate(BaseModel):
    company: str | None = None
    title: str | None = None
    location: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    description: str | None = None


class EmploymentResponse(EmploymentCreate):
    id: str
    created_at: datetime


class EducationCreate(BaseModel):
    user_id: str
    institution: str
    degree: str
    field_of_study: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    grade: str | None = None


class EducationUpdate(BaseModel):
    institution: str | None = None
    degree: str | None = None
    field_of_study: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    grade: str | None = None


class EducationResponse(EducationCreate):
    id: str
    created_at: datetime


class SkillCreate(BaseModel):
    user_id: str
    skill_name: str
    skill_type: str
    proficiency_level: str | None = None


class SkillResponse(SkillCreate):
    id: str
    created_at: datetime


class PracticeInterviewCreate(BaseModel):
    sample_role_type: str
    status: str | None = None


class PracticeInterviewUpdate(BaseModel):
    status: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    duration_seconds: int | None = None
    feedback: str | None = None


class PracticeInterviewResponse(BaseModel):
    id: str
    user_id: str
    sample_role_type: str
    status: str
    started_at: datetime | None
    ended_at: datetime | None
    duration_seconds: int | None
    feedback: str | None
    created_at: datetime


class DeletionRequestCreate(BaseModel):
    request_type: str = "full_deletion"
    reason: str | None = None


class DeletionRequestResponse(BaseModel):
    id: str
    user_id: str
    request_type: str
    status: str
    reason: str | None
    notes: str | None
    requested_at: datetime
    processed_at: datetime | None
    processed_by: str | None


class CandidateApplicationJobRole(BaseModel):
    id: str
    title: str
    organisations: dict | None = None


class CandidateApplicationResponse(BaseModel):
    id: str
    job_role_id: str
    candidate_profile_id: str
    status: str
    source: str | None = None
    source_channel: str | None = None
    profile_confirmed_at: datetime | None = None
    profile_review_status: str | None = None
    created_at: datetime
    updated_at: datetime
    job_roles: CandidateApplicationJobRole | None = None


class CandidateProfileConfirmRequest(BaseModel):
    application_id: str | None = None
    invitation_token: str | None = None


class CandidateProfileConfirmResponse(BaseModel):
    ok: bool
    profile_confirmed_at: datetime
    interview_unlocked: bool = True
