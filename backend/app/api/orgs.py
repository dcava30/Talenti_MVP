import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_org_member
from app.models import Application, Interview, InterviewScore, JobRole, Organisation, OrgEnvironmentInput, OrgUser, User
from app.schemas.orgs import (
    OrgEnvironmentSetup,
    OrgEnvironmentSetupResponse,
    OrgMembershipResponse,
    OrgRetentionUpdate,
    OrgStatsResponse,
    OrganisationCreate,
    OrganisationDetail,
    OrganisationResponse,
    VariableSignalResponse,
)
from app.services.org_environment import (
    build_values_framework_from_translation,
    translate_answers_to_environment,
)

router = APIRouter(prefix="/api/orgs", tags=["orgs"])


def _default_values_framework() -> dict[str, Any]:
    # Canonical 5-dimension default — keeps scoring usable for newly created orgs.
    return {
        "operating_environment": {
            "control_vs_autonomy": "guided_ownership",
            "outcome_vs_process": "balanced",
            "conflict_style": "healthy_debate",
            "decision_reality": "evidence_led",
            "ambiguity_load": "evolving",
            "high_performance_archetype": "strong_owner",
            "dimension_weights": {
                "ownership": 0.25,
                "execution": 0.25,
                "challenge": 0.20,
                "ambiguity": 0.15,
                "feedback": 0.15,
            },
            "fatal_risks": [],
            "coachable_risks": [],
        },
        "taxonomy": {
            "taxonomy_id": "talenti_canonical_v2",
            "version": "2026.2",
            "signals": [
                # ── Ownership ────────────────────────────────────────────────
                {
                    "signal_id": "ownership_accountability",
                    "dimension": "ownership",
                    "description": "Takes clear personal accountability for outcomes.",
                    "score_map": {"strong": 3, "moderate": 2, "weak": 1, "not_observed": 0},
                    "tags": ["ownership"],
                    "evidence_hints": ["I was responsible", "I owned", "my decision", "I led", "I drove"],
                },
                {
                    "signal_id": "ownership_proactivity",
                    "dimension": "ownership",
                    "description": "Acts without being asked; spots gaps and self-initiates.",
                    "score_map": {"strong": 3, "moderate": 2, "weak": 1, "not_observed": 0},
                    "tags": ["ownership"],
                    "evidence_hints": ["without being asked", "I noticed", "I proposed", "I started"],
                },
                {
                    "signal_id": "ownership_follow_through",
                    "dimension": "ownership",
                    "description": "Follows through to resolution, not just initiation.",
                    "score_map": {"strong": 3, "moderate": 2, "weak": 1, "not_observed": 0},
                    "tags": ["ownership"],
                    "evidence_hints": ["I fixed it", "I resolved", "I stepped up", "I handled it"],
                },
                # ── Execution ────────────────────────────────────────────────
                {
                    "signal_id": "execution_delivery",
                    "dimension": "execution",
                    "description": "Delivers reliably; ships things that reach real users.",
                    "score_map": {"strong": 3, "moderate": 2, "weak": 1, "not_observed": 0},
                    "tags": ["execution"],
                    "evidence_hints": ["I delivered", "shipped", "launched", "went live", "hit the target"],
                },
                {
                    "signal_id": "execution_pace_focus",
                    "dimension": "execution",
                    "description": "Maintains pace and prioritises ruthlessly under pressure.",
                    "score_map": {"strong": 3, "moderate": 2, "weak": 1, "not_observed": 0},
                    "tags": ["execution"],
                    "evidence_hints": ["moved quickly", "prioritised", "cut scope", "stayed on track"],
                },
                {
                    "signal_id": "execution_measurable_outcome",
                    "dimension": "execution",
                    "description": "Cites specific, measurable outcomes — not just activity.",
                    "score_map": {"strong": 3, "moderate": 2, "weak": 1, "not_observed": 0},
                    "tags": ["execution"],
                    "evidence_hints": ["measured", "outcome was", "improved by", "reduced", "saved"],
                },
                # ── Challenge ────────────────────────────────────────────────
                {
                    "signal_id": "challenge_constructive_pushback",
                    "dimension": "challenge",
                    "description": "Names disagreement clearly and constructively.",
                    "score_map": {"strong": 3, "moderate": 2, "weak": 1, "not_observed": 0},
                    "tags": ["challenge"],
                    "evidence_hints": ["I disagreed", "I pushed back", "I challenged", "I flagged"],
                },
                {
                    "signal_id": "challenge_stakeholder_navigation",
                    "dimension": "challenge",
                    "description": "Navigates competing interests across stakeholders.",
                    "score_map": {"strong": 3, "moderate": 2, "weak": 1, "not_observed": 0},
                    "tags": ["challenge"],
                    "evidence_hints": ["competing priorities", "I aligned", "I facilitated", "conflicting"],
                },
                {
                    "signal_id": "challenge_problem_naming",
                    "dimension": "challenge",
                    "description": "Names the real problem, not just the surface issue.",
                    "score_map": {"strong": 3, "moderate": 2, "weak": 1, "not_observed": 0},
                    "tags": ["challenge"],
                    "evidence_hints": ["root cause", "identified the issue", "the real issue", "I named"],
                },
                # ── Ambiguity ────────────────────────────────────────────────
                {
                    "signal_id": "ambiguity_operates_without_direction",
                    "dimension": "ambiguity",
                    "description": "Creates structure and moves forward without a clear brief.",
                    "score_map": {"strong": 3, "moderate": 2, "weak": 1, "not_observed": 0},
                    "tags": ["ambiguity"],
                    "evidence_hints": ["no clear brief", "figured it out", "defined the scope", "green field"],
                },
                {
                    "signal_id": "ambiguity_iterates_under_change",
                    "dimension": "ambiguity",
                    "description": "Adapts plan when requirements shift; doesn't get stuck.",
                    "score_map": {"strong": 3, "moderate": 2, "weak": 1, "not_observed": 0},
                    "tags": ["ambiguity"],
                    "evidence_hints": ["changed approach", "pivoted", "requirements changed", "adjusted the plan"],
                },
                {
                    "signal_id": "ambiguity_tests_assumptions",
                    "dimension": "ambiguity",
                    "description": "Validates assumptions through low-cost experiments.",
                    "score_map": {"strong": 3, "moderate": 2, "weak": 1, "not_observed": 0},
                    "tags": ["ambiguity"],
                    "evidence_hints": ["hypothesis", "experiment", "tested assumption", "validated"],
                },
                # ── Feedback ─────────────────────────────────────────────────
                {
                    "signal_id": "feedback_seeks_feedback",
                    "dimension": "feedback",
                    "description": "Actively seeks feedback rather than waiting for it.",
                    "score_map": {"strong": 3, "moderate": 2, "weak": 1, "not_observed": 0},
                    "tags": ["feedback"],
                    "evidence_hints": ["I asked for feedback", "I sought input", "I checked in"],
                },
                {
                    "signal_id": "feedback_acts_on_feedback",
                    "dimension": "feedback",
                    "description": "Applies feedback and demonstrates changed behaviour.",
                    "score_map": {"strong": 3, "moderate": 2, "weak": 1, "not_observed": 0},
                    "tags": ["feedback"],
                    "evidence_hints": ["after the feedback", "I took that on board", "I applied it", "I improved"],
                },
                {
                    "signal_id": "feedback_reflective_learning",
                    "dimension": "feedback",
                    "description": "Reflects honestly on failures and draws clear lessons.",
                    "score_map": {"strong": 3, "moderate": 2, "weak": 1, "not_observed": 0},
                    "tags": ["feedback"],
                    "evidence_hints": ["reflected on", "learned from", "made me think", "recognised I need"],
                },
            ],
        },
    }


def _resolve_values_framework(raw: dict[str, Any] | str | None) -> str:
    # Always seed the canonical default when no framework is provided.
    # Production orgs without a completed environment setup still get a safe,
    # working default rather than silently breaking scoring calls.
    if raw is None:
        return json.dumps(_default_values_framework())

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


@router.post("/{organisation_id}/environment", response_model=OrgEnvironmentSetupResponse)
def setup_org_environment(
    organisation_id: str,
    payload: OrgEnvironmentSetup,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OrgEnvironmentSetupResponse:
    """
    Submit the 10 org environment questions and translate them deterministically
    into operating environment variables. Updates the org's values_framework.

    Persists the raw answers and translation lineage to org_environment_inputs
    for full audit traceability.

    Only org admins may update the environment setup.
    """
    require_org_member(organisation_id, db, user)
    organisation = db.get(Organisation, organisation_id)
    if not organisation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found")

    # Check caller is an admin member
    membership = (
        db.query(OrgUser)
        .filter(OrgUser.organisation_id == organisation_id, OrgUser.user_id == user.id)
        .first()
    )
    if not membership or membership.role not in ("admin", "owner"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organisation admins can update the environment setup.",
        )

    # ── Translate answers → environment variables ─────────────────────────
    answers = payload.to_answers_dict()
    translation = translate_answers_to_environment(answers)

    # ── Build the full values_framework (env + canonical taxonomy) ────────
    values_framework = build_values_framework_from_translation(translation)

    # ── Persist audit record ──────────────────────────────────────────────
    env_input = OrgEnvironmentInput(
        organisation_id=organisation_id,
        raw_answers=json.dumps(translation.raw_answers),
        signals_json=json.dumps([
            {
                "question_id": s.question_id,
                "answer": s.answer,
                "variable": s.variable,
                "derived_value": s.derived_value,
                "weight": s.weight,
            }
            for s in translation.signals
        ]),
        derived_environment=json.dumps(translation.environment),
        defaulted_variables=json.dumps(translation.defaulted_variables),
        extra_fatal_risks=json.dumps(translation.extra_fatal_risks),
        submitted_by=user.id,
        created_at=datetime.utcnow(),
    )
    db.add(env_input)
    db.flush()

    # ── Update the organisation values_framework ──────────────────────────
    organisation.values_framework = json.dumps(values_framework)
    organisation.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(env_input)

    return OrgEnvironmentSetupResponse(
        org_id=organisation_id,
        input_id=env_input.id,
        derived_environment=translation.environment,
        defaulted_variables=translation.defaulted_variables,
        extra_fatal_risks=translation.extra_fatal_risks,
        signals=[
            VariableSignalResponse(
                question_id=s.question_id,
                answer=s.answer,
                variable=s.variable,
                derived_value=s.derived_value,
                weight=s.weight,
            )
            for s in translation.signals
        ],
        values_framework_updated=True,
    )
