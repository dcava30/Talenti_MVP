from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_org_admin
from app.core.config import settings
from app.models import Application, Interview, JobRole, Organisation, User
from app.schemas.tds_shadow_comparison import (
    OrganisationShadowComparisonSummaryResponse,
    RoleShadowComparisonSummaryResponse,
    TdsShadowComparisonResponse,
)
from app.services.tds_shadow_comparison import (
    get_shadow_comparison_for_interview,
    list_shadow_comparisons_for_role,
    summarize_shadow_comparisons_for_organisation,
    summarize_shadow_comparisons_for_role,
)

router = APIRouter(
    prefix="/api/v1/internal/tds-shadow-comparison",
    tags=["internal-tds-shadow-comparison"],
    include_in_schema=settings.tds_shadow_comparison_api_enabled,
)


def _require_comparison_admin(db: Session, org_id: str, user: User) -> None:
    # TODO: replace org-admin inspection access with platform/internal scopes before wider rollout.
    try:
        require_org_admin(org_id, db, user)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_403_FORBIDDEN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only organisation admins can access this resource.",
            ) from exc
        raise


def _ensure_comparison_api_enabled() -> None:
    if not settings.tds_shadow_comparison_api_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="TDS shadow comparison API is not available.",
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


def _get_organisation_or_404(db: Session, organisation_id: str) -> Organisation:
    organisation = db.get(Organisation, organisation_id)
    if organisation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found")
    return organisation


@router.get("/interviews/{interview_id}", response_model=TdsShadowComparisonResponse)
def get_interview_shadow_comparison(
    interview_id: str,
    _: None = Depends(_ensure_comparison_api_enabled),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TdsShadowComparisonResponse:
    interview = _get_interview_or_404(db, interview_id)
    application = _get_application_or_404(db, interview.application_id)
    role = _get_role_or_404(db, application.job_role_id)
    _require_comparison_admin(db, role.organisation_id, user)

    comparison = get_shadow_comparison_for_interview(db, interview_id=interview_id)
    if comparison is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
    return comparison


@router.get("/roles/{role_id}", response_model=list[TdsShadowComparisonResponse])
def list_role_shadow_comparisons(
    role_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: None = Depends(_ensure_comparison_api_enabled),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[TdsShadowComparisonResponse]:
    role = _get_role_or_404(db, role_id)
    _require_comparison_admin(db, role.organisation_id, user)
    return list_shadow_comparisons_for_role(db, role_id=role_id, limit=limit, offset=offset)


@router.get("/roles/{role_id}/summary", response_model=RoleShadowComparisonSummaryResponse)
def get_role_shadow_comparison_summary(
    role_id: str,
    _: None = Depends(_ensure_comparison_api_enabled),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RoleShadowComparisonSummaryResponse:
    role = _get_role_or_404(db, role_id)
    _require_comparison_admin(db, role.organisation_id, user)
    return summarize_shadow_comparisons_for_role(
        db,
        role_id=role_id,
        organisation_id=role.organisation_id,
    )


@router.get(
    "/orgs/{organisation_id}/summary",
    response_model=OrganisationShadowComparisonSummaryResponse,
)
def get_organisation_shadow_comparison_summary(
    organisation_id: str,
    _: None = Depends(_ensure_comparison_api_enabled),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OrganisationShadowComparisonSummaryResponse:
    organisation = _get_organisation_or_404(db, organisation_id)
    _require_comparison_admin(db, organisation.id, user)
    return summarize_shadow_comparisons_for_organisation(db, organisation_id=organisation.id)
