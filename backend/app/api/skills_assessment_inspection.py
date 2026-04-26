from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_org_admin
from app.core.config import settings
from app.models import Application, Interview, JobRole, OrgUser, SkillsAssessmentSummary, User
from app.schemas.skills_assessment_inspection import (
    SkillsAssessmentSummaryInspectionDetailResponse,
    SkillsAssessmentSummaryInspectionSummaryResponse,
)
from app.services.skills_assessment_read_model import (
    enforce_skills_decisioning_exclusion,
    sanitize_skills_human_readable_summary,
    sanitize_skills_source_references,
)
from app.services.skills_assessment_summary import (
    decode_skills_assessment_summary_payloads,
    get_latest_skills_assessment_summary_for_interview,
    get_skills_assessment_summary_by_id,
    list_skills_assessment_summaries_for_candidate,
    list_skills_assessment_summaries_for_role,
)

router = APIRouter(
    prefix="/api/v1/internal/skills-assessment-summaries",
    tags=["internal-skills-assessment-inspection"],
    include_in_schema=settings.tds_skills_summary_inspection_api_enabled,
)


def _require_inspection_admin(db: Session, org_id: str, user: User) -> None:
    # TODO: tighten this to platform/internal scopes before any exposure beyond org admin inspection.
    try:
        require_org_admin(org_id, db, user)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_403_FORBIDDEN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only organisation admins can access this resource.",
            ) from exc
        raise


def _ensure_inspection_api_enabled() -> None:
    if not settings.tds_skills_summary_inspection_api_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skills assessment summary inspection API is not available.",
        )


def _get_interview_for_inspection(db: Session, interview_id: str) -> Interview:
    interview = db.get(Interview, interview_id)
    if interview is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
    return interview


def _get_role_for_inspection(db: Session, role_id: str) -> JobRole:
    role = db.get(JobRole, role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return role


def _get_application_for_inspection(db: Session, application_id: str) -> Application:
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    return application


def _get_admin_org_ids(db: Session, user: User) -> list[str]:
    return list(
        db.execute(
            select(OrgUser.organisation_id)
            .where(OrgUser.user_id == user.id)
            .where(OrgUser.role.in_(("admin", "owner")))
        ).scalars()
    )


def _build_skills_summary_summary(
    summary: SkillsAssessmentSummary,
) -> SkillsAssessmentSummaryInspectionSummaryResponse:
    return SkillsAssessmentSummaryInspectionSummaryResponse(
        skills_summary_id=summary.id,
        interview_id=summary.interview_id,
        candidate_id=summary.candidate_id,
        role_id=summary.role_id,
        organisation_id=summary.organisation_id,
        evidence_strength=summary.evidence_strength,
        confidence=summary.confidence,
        human_readable_summary=sanitize_skills_human_readable_summary(summary.human_readable_summary),
        requires_human_review=summary.requires_human_review,
        excluded_from_tds_decisioning=enforce_skills_decisioning_exclusion(summary.excluded_from_tds_decisioning),
        model_version=summary.model_version,
        created_at=summary.created_at,
    )


def _build_skills_summary_detail(
    summary: SkillsAssessmentSummary,
) -> SkillsAssessmentSummaryInspectionDetailResponse:
    decoded = decode_skills_assessment_summary_payloads(summary)
    return SkillsAssessmentSummaryInspectionDetailResponse(
        **_build_skills_summary_summary(summary).model_dump(mode="python"),
        observed_competencies=decoded["observed_competencies"],
        competency_coverage=decoded["competency_coverage"],
        skill_gaps=decoded["skill_gaps"],
        source_references=sanitize_skills_source_references(decoded["source_references"]),
    )


def _get_skills_summary_or_404(db: Session, summary_id: str) -> SkillsAssessmentSummary:
    summary = get_skills_assessment_summary_by_id(db, summary_id=summary_id)
    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skills assessment summary not found",
        )
    return summary


@router.get(
    "/interviews/{interview_id}/latest",
    response_model=SkillsAssessmentSummaryInspectionDetailResponse,
)
def get_latest_interview_skills_assessment_summary(
    interview_id: str,
    _: None = Depends(_ensure_inspection_api_enabled),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SkillsAssessmentSummaryInspectionDetailResponse:
    interview = _get_interview_for_inspection(db, interview_id)
    application = _get_application_for_inspection(db, interview.application_id)
    role = _get_role_for_inspection(db, application.job_role_id)
    _require_inspection_admin(db, role.organisation_id, user)

    summary = get_latest_skills_assessment_summary_for_interview(db, interview_id=interview_id)
    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skills assessment summary not found",
        )
    return _build_skills_summary_detail(summary)


@router.get(
    "/roles/{role_id}",
    response_model=list[SkillsAssessmentSummaryInspectionSummaryResponse],
)
def list_role_skills_assessment_summaries(
    role_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: None = Depends(_ensure_inspection_api_enabled),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[SkillsAssessmentSummaryInspectionSummaryResponse]:
    role = _get_role_for_inspection(db, role_id)
    _require_inspection_admin(db, role.organisation_id, user)
    summaries = list_skills_assessment_summaries_for_role(db, role_id=role_id, limit=limit, offset=offset)
    return [_build_skills_summary_summary(summary) for summary in summaries]


@router.get(
    "/candidates/{candidate_id}",
    response_model=list[SkillsAssessmentSummaryInspectionSummaryResponse],
)
def list_candidate_skills_assessment_summaries(
    candidate_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: None = Depends(_ensure_inspection_api_enabled),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[SkillsAssessmentSummaryInspectionSummaryResponse]:
    admin_org_ids = _get_admin_org_ids(db, user)
    if not admin_org_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organisation admins can access this resource.",
        )

    summaries = list_skills_assessment_summaries_for_candidate(
        db,
        candidate_id=candidate_id,
        organisation_ids=admin_org_ids,
        limit=limit,
        offset=offset,
    )
    return [_build_skills_summary_summary(summary) for summary in summaries]


@router.get("/{summary_id}", response_model=SkillsAssessmentSummaryInspectionDetailResponse)
def get_skills_assessment_summary(
    summary_id: str,
    _: None = Depends(_ensure_inspection_api_enabled),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SkillsAssessmentSummaryInspectionDetailResponse:
    summary = _get_skills_summary_or_404(db, summary_id)
    _require_inspection_admin(db, summary.organisation_id, user)
    return _build_skills_summary_detail(summary)
