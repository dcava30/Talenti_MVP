from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_org_member
from app.models import Application, Interview, InterviewScore, JobRole, Organisation, OrgUser, User
from app.schemas.orgs import (
    OrgMembershipResponse,
    OrgRetentionUpdate,
    OrgStatsResponse,
    OrganisationCreate,
    OrganisationDetail,
    OrganisationResponse,
)

router = APIRouter(prefix="/api/orgs", tags=["orgs"])


@router.post("", response_model=OrganisationResponse)
def create_org(
    payload: OrganisationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OrganisationResponse:
    org = Organisation(
        name=payload.name,
        description=payload.description,
        industry=payload.industry,
        website=payload.website,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(org)
    db.flush()
    membership = OrgUser(
        organisation_id=org.id,
        user_id=user.id,
        role="admin",
        created_at=datetime.utcnow(),
    )
    db.add(membership)
    db.commit()
    db.refresh(org)
    return OrganisationResponse(
        id=org.id,
        name=org.name,
        description=org.description,
        industry=org.industry,
        website=org.website,
        created_at=org.created_at,
    )


@router.get("/current", response_model=OrgMembershipResponse | None)
def get_current_membership(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OrgMembershipResponse | None:
    membership = db.query(OrgUser).filter(OrgUser.user_id == user.id).first()
    if not membership:
        return None
    organisation = db.get(Organisation, membership.organisation_id)
    if not organisation:
        return None
    return OrgMembershipResponse(
        id=membership.id,
        role=membership.role,
        organisation=OrganisationDetail(
            id=organisation.id,
            name=organisation.name,
            description=organisation.description,
            industry=organisation.industry,
            website=organisation.website,
            values_framework=organisation.values_framework,
            recording_retention_days=organisation.recording_retention_days,
            created_at=organisation.created_at,
            updated_at=organisation.updated_at,
        ),
    )


@router.patch("/{organisation_id}/retention", response_model=OrganisationDetail)
def update_retention(
    organisation_id: str,
    payload: OrgRetentionUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OrganisationDetail:
    require_org_member(organisation_id, db, user)
    organisation = db.get(Organisation, organisation_id)
    if not organisation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found")
    organisation.recording_retention_days = payload.recording_retention_days
    organisation.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(organisation)
    return OrganisationDetail(
        id=organisation.id,
        name=organisation.name,
        description=organisation.description,
        industry=organisation.industry,
        website=organisation.website,
        values_framework=organisation.values_framework,
        recording_retention_days=organisation.recording_retention_days,
        created_at=organisation.created_at,
        updated_at=organisation.updated_at,
    )


@router.get("/{organisation_id}/stats", response_model=OrgStatsResponse)
def get_org_stats(
    organisation_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OrgStatsResponse:
    require_org_member(organisation_id, db, user)
    active_roles = (
        db.query(JobRole)
        .filter(JobRole.organisation_id == organisation_id, JobRole.status != "closed")
        .count()
    )
    role_ids = db.query(JobRole.id).filter(JobRole.organisation_id == organisation_id).subquery()
    total_candidates = (
        db.query(Application.candidate_profile_id)
        .filter(Application.job_role_id.in_(role_ids))
        .distinct()
        .count()
    )
    completed_interviews = (
        db.query(Interview)
        .join(Application, Interview.application_id == Application.id)
        .filter(
            Application.job_role_id.in_(role_ids),
            Interview.status == "completed",
        )
        .count()
    )
    avg_match_score = (
        db.query(func.avg(InterviewScore.overall_score))
        .join(Interview, InterviewScore.interview_id == Interview.id)
        .join(Application, Interview.application_id == Application.id)
        .filter(Application.job_role_id.in_(role_ids))
        .scalar()
    )
    return OrgStatsResponse(
        activeRoles=active_roles,
        totalCandidates=total_candidates,
        completedInterviews=completed_interviews,
        avgMatchScore=int(avg_match_score) if avg_match_score is not None else None,
    )
