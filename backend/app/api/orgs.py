import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_org_member
from app.core.config import settings
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


def _default_values_framework() -> dict[str, Any]:
    # Default framework keeps local scoring usable for newly created orgs.
    return {
        "operating_environment": {
            "control_vs_autonomy": "guided_ownership",
            "outcome_vs_process": "balanced",
            "conflict_style": "healthy_debate",
            "decision_reality": "evidence_led",
            "ambiguity_load": "evolving",
            "high_performance_archetype": "strong_owner",
            "dimension_weights": {
                "ownership": 0.4,
                "communication": 0.3,
                "adaptability": 0.3,
            },
            "fatal_risks": [],
            "coachable_risks": [],
        },
        "taxonomy": {
            "taxonomy_id": "talenti_default_v1",
            "version": "2026.1",
            "signals": [
                {
                    "signal_id": "ownership_follow_through",
                    "dimension": "ownership",
                    "description": "Demonstrates clear ownership and follow-through.",
                    "score_map": {
                        "strong": 3,
                        "moderate": 2,
                        "weak": 1,
                        "not_observed": 0,
                    },
                    "tags": [],
                    "evidence_hints": ["owned", "delivered", "accountable"],
                },
                {
                    "signal_id": "clear_structured_communication",
                    "dimension": "communication",
                    "description": "Communicates with clarity and structure.",
                    "score_map": {
                        "strong": 3,
                        "moderate": 2,
                        "weak": 1,
                        "not_observed": 0,
                    },
                    "tags": [],
                    "evidence_hints": ["explained", "clarified", "structured"],
                },
                {
                    "signal_id": "adapts_under_change",
                    "dimension": "adaptability",
                    "description": "Adapts constructively to change and ambiguity.",
                    "score_map": {
                        "strong": 3,
                        "moderate": 2,
                        "weak": 1,
                        "not_observed": 0,
                    },
                    "tags": [],
                    "evidence_hints": ["adapted", "changed approach", "iterated"],
                },
            ],
        },
    }


def _resolve_values_framework(raw: dict[str, Any] | str | None) -> str | None:
    if raw is None:
        if settings.environment.lower() in {"development", "dev", "local", "test"}:
            return json.dumps(_default_values_framework())
        return None

    parsed: dict[str, Any]
    if isinstance(raw, str):
        try:
            decoded = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="values_framework must be valid JSON.",
            ) from exc
        if not isinstance(decoded, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="values_framework JSON must be an object.",
            )
        parsed = decoded
    elif isinstance(raw, dict):
        parsed = raw
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="values_framework must be a JSON object or JSON string.",
        )

    if "operating_environment" not in parsed or "taxonomy" not in parsed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="values_framework must include operating_environment and taxonomy.",
        )
    return json.dumps(parsed)


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
        values_framework=_resolve_values_framework(payload.values_framework),
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
