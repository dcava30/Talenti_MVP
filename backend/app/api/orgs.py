import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_org_member
from app.models import Application, Interview, InterviewScore, JobRole, Organisation, OrgEnvironmentInput, OrgUser, User
from app.schemas.orgs import (
    AggregatedEnvironmentResponse,
    MIN_QUESTIONS_PER_RESPONDENT,
    MultiRespondentEnvironmentSetup,
    OrgEnvironmentSetup,
    OrgEnvironmentSetupResponse,
    OrgMembershipResponse,
    OrgRetentionUpdate,
    OrgStatsResponse,
    OrganisationCreate,
    OrganisationDetail,
    OrganisationResponse,
    VariableAggregationResponse,
    VariableSignalResponse,
)
from app.services.org_environment import (
    aggregate_environment_translations,
    build_values_framework_from_translation,
    translate_answers_to_environment,
)

router = APIRouter(prefix="/api/orgs", tags=["orgs"])


def _default_values_framework() -> dict[str, Any]:
    """
    Canonical 5-dimension default framework — keeps scoring usable for newly
    created orgs that haven't completed the environment setup questionnaire.

    Sources taxonomy and weights from app.talenti_canonical — single source of
    truth for the backend. Do not inline the taxonomy here.
    """
    from app.talenti_canonical import CANONICAL_TAXONOMY_V2, DEFAULT_DIMENSION_WEIGHTS
    return {
        "operating_environment": {
            "control_vs_autonomy": "guided_ownership",
            "outcome_vs_process": "balanced",
            "conflict_style": "healthy_debate",
            "decision_reality": "evidence_led",
            "ambiguity_load": "evolving",
            "high_performance_archetype": "strong_owner",
            "dimension_weights": DEFAULT_DIMENSION_WEIGHTS.copy(),
            "fatal_risks": [],
            "coachable_risks": [],
        },
        "taxonomy": CANONICAL_TAXONOMY_V2,
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


@router.post("/{organisation_id}/environment/aggregate", response_model=AggregatedEnvironmentResponse)
def aggregate_org_environment(
    organisation_id: str,
    payload: MultiRespondentEnvironmentSetup,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AggregatedEnvironmentResponse:
    """
    Submit questionnaire responses from multiple stakeholders and aggregate them
    into a single operating environment using weighted majority voting.

    Design:
    - Each respondent's answers are translated independently via the deterministic
      rubric, then merged using aggregate_environment_translations().
    - Null exclusion: missing answers from a respondent don't contribute any weight.
    - Contested variables (no clear majority across respondents) are flagged in
      the response so a reviewer can resolve them manually.
    - environment_confidence (high | medium | low) reflects overall agreement.
    - When confidence is low, the values_framework is still updated but a
      reviewer_flag is added — downstream scoring will cap recommendations at
      "caution" until the environment is confirmed.

    Minimum completeness gate: each respondent must have answered at least
    MIN_QUESTIONS_PER_RESPONDENT questions (default 6). Submissions below this
    are rejected with 422.

    Only org admins may update the environment setup.
    """
    require_org_member(organisation_id, db, user)
    organisation = db.get(Organisation, organisation_id)
    if not organisation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found")

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

    # ── Minimum completeness gate ────────────────────────────────────────
    incomplete = [
        i + 1
        for i, r in enumerate(payload.respondents)
        if r.answered_count() < MIN_QUESTIONS_PER_RESPONDENT
    ]
    if incomplete:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Respondent(s) {incomplete} answered fewer than "
                f"{MIN_QUESTIONS_PER_RESPONDENT} questions. "
                "Each respondent must answer at least "
                f"{MIN_QUESTIONS_PER_RESPONDENT} of the 10 questions."
            ),
        )

    # ── Translate each respondent independently ──────────────────────────
    translations = [
        translate_answers_to_environment(r.to_answers_dict())
        for r in payload.respondents
    ]

    # ── Aggregate ────────────────────────────────────────────────────────
    agg = aggregate_environment_translations(translations)

    # ── Build reviewer flags ─────────────────────────────────────────────
    reviewer_flags: list[str] = []
    if agg.contested_variables:
        reviewer_flags.append(
            f"Contested variables require manual review: {', '.join(agg.contested_variables)}. "
            "Respondents gave conflicting answers — the majority value was used but "
            "consider re-running with more respondents or resolving manually."
        )
    if agg.defaulted_variables:
        reviewer_flags.append(
            f"Variables defaulted (no respondent answered): {', '.join(agg.defaulted_variables)}."
        )
    if agg.environment_confidence == "low":
        reviewer_flags.append(
            "Environment confidence is LOW. Hiring recommendations will be capped at "
            "'caution' until the environment is confirmed by resolving contested variables."
        )

    # ── Build and persist the values_framework ───────────────────────────
    # We need a single TranslationResult-like object to pass to the framework builder.
    # We synthesise one from the aggregated result.
    from app.services.org_environment import TranslationResult, VariableSignal
    synthetic_translation = TranslationResult(
        environment=agg.environment,
        signals=[],
        defaulted_variables=agg.defaulted_variables,
        extra_fatal_risks=agg.extra_fatal_risks,
        raw_answers={},
    )
    values_framework = build_values_framework_from_translation(synthetic_translation)

    # Store environment_confidence in the framework so downstream scoring can read it
    values_framework["operating_environment"]["environment_confidence"] = agg.environment_confidence

    # ── Persist one OrgEnvironmentInput per respondent ───────────────────
    for i, (respondent, translation) in enumerate(zip(payload.respondents, translations)):
        label = respondent.respondent_label or f"respondent_{i + 1}"
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

    organisation.values_framework = json.dumps(values_framework)
    organisation.updated_at = datetime.utcnow()
    db.commit()

    return AggregatedEnvironmentResponse(
        org_id=organisation_id,
        respondent_count=agg.respondent_count,
        environment_confidence=agg.environment_confidence,
        derived_environment=agg.environment,
        variable_aggregations={
            v: VariableAggregationResponse(
                variable=va.variable,
                resolved_value=va.resolved_value,
                top_value_weight_share=va.top_value_weight_share,
                all_responded_values=va.all_responded_values,
                is_contested=va.is_contested,
                respondent_count=va.respondent_count,
                is_defaulted=va.is_defaulted,
            )
            for v, va in agg.variable_aggregations.items()
        },
        contested_variables=agg.contested_variables,
        defaulted_variables=agg.defaulted_variables,
        extra_fatal_risks=agg.extra_fatal_risks,
        values_framework_updated=True,
        reviewer_flags=reviewer_flags,
    )
