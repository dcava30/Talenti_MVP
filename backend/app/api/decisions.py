from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_org_member
from app.core.config import settings
from app.models import Application, Interview, JobRole, User
from app.schemas.decisions import RecruiterDecisionResponse
from app.services.decision_persistence import get_latest_decision_for_interview
from app.services.decision_read_model import build_recruiter_decision_response

router = APIRouter(
    tags=["decisions"],
    include_in_schema=settings.tds_recruiter_decision_api_enabled,
)


def _ensure_recruiter_decision_api_enabled() -> None:
    if not settings.tds_recruiter_decision_api_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recruiter decision API is not available.",
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


@router.get("/api/v1/interviews/{interview_id}/decision", response_model=RecruiterDecisionResponse)
def get_latest_recruiter_interview_decision(
    interview_id: str,
    _: None = Depends(_ensure_recruiter_decision_api_enabled),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RecruiterDecisionResponse:
    interview = _get_interview_or_404(db, interview_id)
    application = _get_application_or_404(db, interview.application_id)
    role = _get_role_or_404(db, application.job_role_id)
    require_org_member(role.organisation_id, db, user)

    decision = get_latest_decision_for_interview(db, interview_id=interview_id)
    if decision is None or decision.organisation_id != role.organisation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found")
    return build_recruiter_decision_response(decision)
