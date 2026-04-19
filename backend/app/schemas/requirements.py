from typing import List, Optional
from pydantic import BaseModel


class ExtractRequirementsRequest(BaseModel):
    job_description: str


class ExtractRequirementsResponse(BaseModel):
    skills: list[str]
    responsibilities: list[str]
    qualifications: list[str]


# ── Skills parsing schemas ───────────────────────────────────────────────────

class JobExpectationSchema(BaseModel):
    competency: str
    level: str  # "must" | "nice"
    min_years: float = 0.0
    keywords: List[str] = []
    threshold: float = 0.65


class JobProfileSchema(BaseModel):
    role_title: str
    seniority: str
    expectations: List[JobExpectationSchema]
    weights: dict = {"resume": 0.40, "interview": 0.50, "experience_years": 0.10}
    decision_thresholds: dict = {"pass": 75.0, "review": 60.0, "fail": 0.0}


class ParseSkillsRequest(BaseModel):
    job_description: str
    role_title: Optional[str] = None


class ParseSkillsResponse(BaseModel):
    job_profile: JobProfileSchema
