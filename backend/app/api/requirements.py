from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import User
from app.schemas.requirements import (
    ExtractRequirementsRequest,
    ExtractRequirementsResponse,
    ParseSkillsRequest,
    ParseSkillsResponse,
    JobExpectationSchema,
    JobProfileSchema,
)
from app.services.jd_parser import parse_job_description

router = APIRouter(prefix="/api/v1/roles", tags=["roles-ai"])


@router.post("/extract-requirements", response_model=ExtractRequirementsResponse)
def extract_requirements(
    payload: ExtractRequirementsRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ExtractRequirementsResponse:
    if not payload.job_description:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Job description required")

    sentences = [s.strip() for s in payload.job_description.split(".") if s.strip()]
    skills = [s for s in sentences if "experience" in s.lower()]
    responsibilities = sentences[:3]
    qualifications = sentences[3:6]

    return ExtractRequirementsResponse(
        skills=skills,
        responsibilities=responsibilities,
        qualifications=qualifications,
    )


@router.post("/parse-skills", response_model=ParseSkillsResponse)
def parse_skills(
    payload: ParseSkillsRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ParseSkillsResponse:
    if not payload.job_description:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Job description required")

    profile = parse_job_description(payload.job_description, payload.role_title or "")

    expectations = [
        JobExpectationSchema(
            competency=exp.competency,
            level=exp.level,
            min_years=exp.min_years,
            keywords=list(exp.keywords),
            threshold=exp.threshold,
        )
        for exp in profile.expectations
    ]

    return ParseSkillsResponse(
        job_profile=JobProfileSchema(
            role_title=profile.role_title,
            seniority=profile.seniority,
            expectations=expectations,
            weights=profile.weights,
            decision_thresholds=profile.decision_thresholds,
        )
    )
