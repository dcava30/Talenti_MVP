from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_org_member
from app.core.config import settings
from app.models import Application, Interview, JobRole, User
from app.schemas.skills_assessment_summaries import RecruiterSkillsAssessmentSummaryResponse
from app.services.skills_assessment_read_model import (
    build_recruiter_skills_assessment_summary_response,
)
from app.services.skills_assessment_summary import get_latest_skills_assessment_summary_for_interview

router = APIRouter(
    tags=["skills-assessment-summaries"],
    include_in_schema=settings.tds_recruiter_skills_summary_api_enabled,
)


def _ensure_recruiter_skills_summary_api_enabled() -> None:
    if not settings.tds_recruiter_skills_summary_api_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recruiter skills assessment summary API is not available.",
        )


def _get_interview_or_404(db: Session, interview_id: str) -> Interview:
    interview = db.get(Interview, interview_id)
    if interview is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
    return interview


def _get_application_or_404(db: Session, application_id: str) -> Application:
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    return application


def _get_role_or_404(db: Session, role_id: str) -> JobRole:
    role = db.get(JobRole, role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return role


@router.get(
    "/api/v1/interviews/{interview_id}/skills-assessment-summary",
    response_model=RecruiterSkillsAssessmentSummaryResponse,
)
def get_latest_recruiter_interview_skills_assessment_summary(
    interview_id: str,
    _: None = Depends(_ensure_recruiter_skills_summary_api_enabled),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RecruiterSkillsAssessmentSummaryResponse:
    interview = _get_interview_or_404(db, interview_id)
    application = _get_application_or_404(db, interview.application_id)
    role = _get_role_or_404(db, application.job_role_id)
    require_org_member(role.organisation_id, db, user)

    summary = get_latest_skills_assessment_summary_for_interview(db, interview_id=interview_id)
    if summary is None or summary.organisation_id != role.organisation_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skills assessment summary not found",
        )
    return build_recruiter_skills_assessment_summary_response(summary)
