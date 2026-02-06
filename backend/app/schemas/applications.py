from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ApplicationCreate(BaseModel):
    job_role_id: str
    candidate_profile_id: str
    status: str | None = None
    source: str | None = None
    cover_letter: str | None = None


class ApplicationUpdate(BaseModel):
    status: str | None = None
    source: str | None = None
    cover_letter: str | None = None


class ApplicationResponse(BaseModel):
    id: str
    job_role_id: str
    candidate_profile_id: str
    status: str
    source: str | None
    cover_letter: str | None
    created_at: datetime
    updated_at: datetime


class JobContext(BaseModel):
    id: str
    title: str
    description: str | None = None
    requirements: Any | None = None
    interview_questions: Any | None = None


class OrgContext(BaseModel):
    id: str
    name: str
    values_framework: Any | None = None


class CandidateContext(BaseModel):
    id: str
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    skills: list[str] = []
    experience_years: int | None = None
    recent_roles: list[str] = []
    education_level: str | None = None


class ApplicationContextResponse(BaseModel):
    job: JobContext | None = None
    org: OrgContext | None = None
    candidate: CandidateContext | None = None
    competencies_covered: list[str] = []
    competencies_to_cover: list[str] = []
