from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import (
    Application,
    DecisionOutcome,
    Interview,
    InterviewScore,
    JobRole,
    OrgEnvironmentInput,
    Organisation,
    ScoreDimension,
    TranscriptSegment,
)
from app.schemas.scoring import (
    BehaviouralDimension,
    CultureFitResult,
    DimensionOutcome,
    SkillScore,
    SkillsFitResult,
)
from app.schemas.decisioning import (
    BehaviouralDecisionInput,
    BehaviouralDimensionEvidence,
    ConfidenceBand as DecisionConfidenceBand,
)
from app.services.culture_fit import CultureContextError, load_org_culture_context
from app.services.decision_layer import evaluate_behavioural_decision
from app.services.decision_persistence import (
    create_decision_audit_event,
    create_decision_outcome_from_result,
    get_latest_decision_for_interview_version,
)
from app.services.skills_assessment_mapper import (
    SkillsAssessmentSummaryPayload,
    map_model_service_2_output_to_skills_assessment_summary,
)
from app.services.skills_assessment_summary import (
    create_skills_assessment_summary,
    get_latest_skills_assessment_summary_for_interview_model_version,
)
from app.services.ml_client import MLServiceError, ml_client
from app.talenti_canonical.dimensions import (
    compute_dimension_requirements,
    get_archetype_fatal_risks,
)

logger = logging.getLogger(__name__)

CANONICAL_DIMENSIONS = ["ownership", "execution", "challenge", "ambiguity", "feedback"]
DECISION_LAYER_SHADOW_CONTEXT_KEYS = {
    "interview_id",
    "candidate_id",
    "role_id",
    "organisation_id",
    "environment_profile",
    "environment_confidence",
    "behavioural_dimension_evidence",
    "critical_dimensions",
    "minimum_dimensions",
    "priority_dimensions",
    "rule_version",
    "policy_version",
}


class InterviewScoringError(RuntimeError):
    pass


def _to_decision_confidence_band(value: str | None) -> DecisionConfidenceBand:
    mapping = {
        "high": DecisionConfidenceBand.HIGH,
        "medium": DecisionConfidenceBand.MEDIUM,
        "low": DecisionConfidenceBand.LOW,
    }
    if value is None:
        return DecisionConfidenceBand.LOW
    return mapping.get(value.strip().lower(), DecisionConfidenceBand.LOW)


def _to_internal_behavioural_score(score: int) -> int:
    """
    Map the existing 0-100 culture-fit score into the signed TDS shadow scale.

    This helper keeps the Decision Layer dark and deterministic without changing
    the production scoring contract. The thresholds roughly follow the backend's
    current pass/watch segmentation:
      70+ -> +2
      55+ -> +1
      40+ ->  0
      25+ -> -1
      else -> -2
    """
    if score >= 70:
        return 2
    if score >= 55:
        return 1
    if score >= 40:
        return 0
    if score >= 25:
        return -1
    return -2


def build_behavioural_decision_input_from_scoring_context(
    scoring_context: dict[str, Any],
) -> BehaviouralDecisionInput:
    """
    Dark integration helper for the upcoming behavioural Decision Layer.

    This deliberately reads only the behavioural contract keys from a broader
    scoring context so model-service-2 outputs cannot leak into TDS decisioning.
    The helper is not called by the production scoring flow yet.
    """
    behavioural_context = {
        key: scoring_context[key]
        for key in DECISION_LAYER_SHADOW_CONTEXT_KEYS
        if key in scoring_context
    }
    return BehaviouralDecisionInput.model_validate(behavioural_context)


def build_shadow_behavioural_decision_input(
    *,
    interview_id: str,
    candidate_id: str,
    role_id: str,
    organisation_id: str,
    operating_environment: dict[str, Any],
    culture_fit: CultureFitResult,
    dimension_tiers: dict[str, str] | None = None,
    rule_version: str = "tds-phase2-shadow-v1",
    policy_version: str = "mvp1-behaviour-decides-v1",
) -> BehaviouralDecisionInput:
    """
    Build the behavioural-only TDS payload from the existing scoring context.

    Persistence metadata such as org_environment_input_id is resolved separately
    at the integration point so the Decision Layer contract stays behaviour-only.
    """
    tiers = dimension_tiers or {}
    behavioural_dimension_evidence = [
        BehaviouralDimensionEvidence(
            dimension=dimension.name,
            score_internal=_to_internal_behavioural_score(dimension.score),
            confidence=_to_decision_confidence_band(dimension.confidence_band),
            evidence_summary=dimension.rationale,
            rationale=dimension.rationale,
            valid_signals=list(dimension.matched_signals or []),
            invalid_signals=[],
            conflict_flags=[],
        )
        for dimension in culture_fit.dimensions
        if dimension.name in CANONICAL_DIMENSIONS
    ]

    scoring_context: dict[str, Any] = {
        "interview_id": interview_id,
        "candidate_id": candidate_id,
        "role_id": role_id,
        "organisation_id": organisation_id,
        "environment_profile": dict(operating_environment),
        "environment_confidence": _to_decision_confidence_band(
            operating_environment.get("environment_confidence")
        ),
        "behavioural_dimension_evidence": behavioural_dimension_evidence,
        "critical_dimensions": [
            dimension
            for dimension in CANONICAL_DIMENSIONS
            if tiers.get(dimension) == "Critical"
        ],
        "minimum_dimensions": [
            dimension
            for dimension in CANONICAL_DIMENSIONS
            if tiers.get(dimension) in {"Critical", "Important"}
        ],
        "priority_dimensions": [
            dimension.name
            for dimension in culture_fit.dimensions
            if dimension.name in CANONICAL_DIMENSIONS
        ],
        "rule_version": rule_version,
        "policy_version": policy_version,
    }
    return build_behavioural_decision_input_from_scoring_context(scoring_context)


def _get_latest_org_environment_input_id(
    db: Session,
    *,
    organisation_id: str,
) -> str | None:
    return db.execute(
        select(OrgEnvironmentInput.id)
        .where(OrgEnvironmentInput.organisation_id == organisation_id)
        .order_by(OrgEnvironmentInput.created_at.desc(), OrgEnvironmentInput.id.desc())
        .limit(1)
    ).scalar_one_or_none()


def _run_shadow_behavioural_decision_write(
    db: Session,
    *,
    interview_id: str,
    candidate_id: str,
    role_id: str,
    organisation_id: str,
    operating_environment: dict[str, Any],
    culture_fit: CultureFitResult,
    dimension_tiers: dict[str, str] | None = None,
) -> DecisionOutcome | None:
    decision_input = build_shadow_behavioural_decision_input(
        interview_id=interview_id,
        candidate_id=candidate_id,
        role_id=role_id,
        organisation_id=organisation_id,
        operating_environment=operating_environment,
        culture_fit=culture_fit,
        dimension_tiers=dimension_tiers,
    )
    org_environment_input_id = _get_latest_org_environment_input_id(
        db,
        organisation_id=organisation_id,
    )

    logger.info(
        "TDS shadow decision evaluation started",
        extra={
            "interview_id": interview_id,
            "candidate_id": candidate_id,
            "role_id": role_id,
            "organisation_id": organisation_id,
            "rule_version": decision_input.rule_version,
            "policy_version": decision_input.policy_version,
            "skills_inputs_excluded": True,
        },
    )

    # Idempotency strategy: skip duplicate shadow writes for the same interview
    # and exact rule_version/policy_version pair so reruns do not create
    # indistinguishable duplicates while later policy revisions can still append.
    existing = get_latest_decision_for_interview_version(
        db,
        interview_id=interview_id,
        rule_version=decision_input.rule_version,
        policy_version=decision_input.policy_version,
    )
    if existing is not None:
        logger.info(
            "TDS shadow decision skipped because matching version already exists",
            extra={
                "interview_id": interview_id,
                "decision_id": existing.id,
                "rule_version": decision_input.rule_version,
                "policy_version": decision_input.policy_version,
            },
        )
        return existing

    decision_result = evaluate_behavioural_decision(decision_input)
    decision = create_decision_outcome_from_result(
        db,
        decision_result=decision_result,
        interview_id=interview_id,
        candidate_id=candidate_id,
        role_id=role_id,
        organisation_id=organisation_id,
        org_environment_input_id=org_environment_input_id,
        environment_profile=decision_input.environment_profile,
    )
    create_decision_audit_event(
        db,
        decision_id=decision.id,
        event_type="shadow_decision_evaluated",
        actor_type="system",
        rule_version=decision_result.rule_version,
        policy_version=decision_result.policy_version,
        event_payload={
            "mode": "shadow",
            "interview_id": interview_id,
            "skills_inputs_excluded": True,
            "decision_state": decision_result.decision_state.value,
        },
    )
    logger.info(
        "TDS shadow decision persisted",
        extra={
            "interview_id": interview_id,
            "decision_id": decision.id,
            "rule_version": decision_result.rule_version,
            "policy_version": decision_result.policy_version,
        },
    )
    return decision


def _maybe_run_shadow_behavioural_decision_write(
    db: Session,
    *,
    interview_id: str,
    candidate_id: str,
    role_id: str,
    organisation_id: str,
    operating_environment: dict[str, Any],
    culture_fit: CultureFitResult,
    dimension_tiers: dict[str, str] | None = None,
) -> DecisionOutcome | None:
    if not settings.tds_decision_shadow_write_enabled:
        logger.info(
            "TDS shadow decision skipped because feature flag disabled",
            extra={
                "interview_id": interview_id,
                "candidate_id": candidate_id,
                "role_id": role_id,
                "organisation_id": organisation_id,
            },
        )
        return None

    try:
        with db.begin_nested():
            return _run_shadow_behavioural_decision_write(
                db,
                interview_id=interview_id,
                candidate_id=candidate_id,
                role_id=role_id,
                organisation_id=organisation_id,
                operating_environment=operating_environment,
                culture_fit=culture_fit,
                dimension_tiers=dimension_tiers,
            )
    except Exception:
        logger.warning(
            "TDS shadow decision failed non-fatally",
            extra={
                "interview_id": interview_id,
                "candidate_id": candidate_id,
                "role_id": role_id,
                "organisation_id": organisation_id,
            },
            exc_info=True,
        )
        return None


def _run_shadow_skills_assessment_summary_write(
    db: Session,
    *,
    interview_id: str,
    candidate_id: str,
    role_id: str,
    organisation_id: str,
    model2_result: dict[str, Any],
) -> None:
    logger.info(
        "TDS skills summary shadow mapping started",
        extra={
            "interview_id": interview_id,
            "candidate_id": candidate_id,
            "role_id": role_id,
            "organisation_id": organisation_id,
        },
    )

    payload: SkillsAssessmentSummaryPayload = map_model_service_2_output_to_skills_assessment_summary(
        model2_result
    )
    model_version = payload.get("model_version")

    # Idempotency strategy: skip duplicate shadow writes only when model-service-2
    # supplied a concrete version for the same interview. If the upstream payload
    # omits model_version we allow append-only writes because there is no safe
    # version key to deduplicate against.
    if model_version:
        existing = get_latest_skills_assessment_summary_for_interview_model_version(
            db,
            interview_id=interview_id,
            model_version=model_version,
        )
        if existing is not None:
            logger.info(
                "TDS skills summary shadow duplicate skipped",
                extra={
                    "interview_id": interview_id,
                    "skills_summary_id": existing.id,
                    "model_version": model_version,
                },
            )
            return

    summary = create_skills_assessment_summary(
        db,
        interview_id=interview_id,
        candidate_id=candidate_id,
        role_id=role_id,
        organisation_id=organisation_id,
        **payload,
    )
    logger.info(
        "TDS skills summary shadow persisted",
        extra={
            "interview_id": interview_id,
            "skills_summary_id": summary.id,
            "model_version": summary.model_version,
            "excluded_from_tds_decisioning": summary.excluded_from_tds_decisioning,
        },
    )


def _maybe_run_shadow_skills_assessment_summary_write(
    db: Session,
    *,
    interview_id: str,
    candidate_id: str,
    role_id: str,
    organisation_id: str,
    model2_result: dict[str, Any] | None,
) -> None:
    if not settings.tds_skills_summary_shadow_write_enabled:
        logger.info(
            "TDS skills summary shadow write skipped because feature flag disabled",
            extra={
                "interview_id": interview_id,
                "candidate_id": candidate_id,
                "role_id": role_id,
                "organisation_id": organisation_id,
            },
        )
        return

    if not isinstance(model2_result, dict):
        return

    try:
        with db.begin_nested():
            _run_shadow_skills_assessment_summary_write(
                db,
                interview_id=interview_id,
                candidate_id=candidate_id,
                role_id=role_id,
                organisation_id=organisation_id,
                model2_result=model2_result,
            )
    except Exception:
        logger.warning(
            "TDS skills summary shadow write failed non-fatally",
            extra={
                "interview_id": interview_id,
                "candidate_id": candidate_id,
                "role_id": role_id,
                "organisation_id": organisation_id,
            },
            exc_info=True,
        )


def _parse_rubric(
    raw: dict[str, Any],
) -> tuple[dict[str, float], dict[str, str]]:
    """
    Parse scoring_rubric JSON into separate weights and tiers dicts.

    Supports two formats for backwards compatibility:
      Legacy : {"ownership": 1.5, "execution": 1.2}
      New    : {"ownership": {"weight": 1.5, "tier": "Critical"}, ...}

    Returns
    -------
    weights : {dim: float}   — scoring weight per dimension (default 1.0)
    tiers   : {dim: str}     — importance tier per dimension (default "Standard")
    """
    weights: dict[str, float] = {}
    tiers: dict[str, str] = {}
    valid_tiers = {"Standard", "Important", "Critical"}

    for dim, value in raw.items():
        if not isinstance(dim, str):
            continue
        if isinstance(value, (int, float)):
            # Legacy format: plain weight
            weights[dim] = max(0.0, float(value))
            tiers[dim] = "Standard"
        elif isinstance(value, dict):
            raw_weight = value.get("weight", 1.0)
            raw_tier = value.get("tier", "Standard")
            try:
                weights[dim] = max(0.0, float(raw_weight))
            except (TypeError, ValueError):
                weights[dim] = 1.0
            tiers[dim] = raw_tier if raw_tier in valid_tiers else "Standard"

    return weights, tiers


def _confidence_band(confidence: float | None) -> str | None:
    """
    Map a raw 0-1 confidence float to a discrete label.

    Thresholds:
      ≥ 0.70  →  High    (strong evidence, multiple aligned signals)
      ≥ 0.40  →  Medium  (moderate evidence, some alignment)
      < 0.40  →  Low     (sparse evidence or contradicted signals)
      None    →  None    (no evidence-derived confidence available)
    """
    if confidence is None:
        return None
    if confidence >= 0.70:
        return "High"
    if confidence >= 0.40:
        return "Medium"
    return "Low"


# ── Culture fit extraction ────────────────────────────────────────────────────

def _extract_culture_fit(
    model1_result: dict[str, Any],
    rubric: dict[str, float] | None = None,
) -> CultureFitResult:
    """
    Extract scored behavioural dimensions from model-service-1's response.

    This function is responsible only for extracting and normalising scores.
    Dimension classification (pass/watch/risk) and risk stacking are applied
    separately by the backend's canonical rule engine — see
    classify_dimensions() and compute_risk_stack() below.
    """
    rubric = rubric or {}

    if model1_result.get("error"):
        raise InterviewScoringError(
            f"Culture fit model failed: {model1_result.get('error')}"
        )

    scores_raw = model1_result.get("scores")
    if not isinstance(scores_raw, dict):
        raise InterviewScoringError("Culture fit model returned no scores.")

    dimensions: list[BehaviouralDimension] = []

    for name, data in scores_raw.items():
        if not isinstance(name, str) or not name.strip() or not isinstance(data, dict):
            continue
        if "score" not in data:
            continue
        try:
            raw_score = float(data["score"])
            # Model-service-1 may return normalised 0-1 or already 0-100
            if 0.0 <= raw_score <= 1.0:
                raw_score *= 100.0
            score_value = max(0, min(100, int(round(raw_score))))
        except (TypeError, ValueError):
            logger.warning("Culture fit model: invalid score value for dimension %s", name)
            continue

        # Evidence-derived confidence — do NOT use a hardcoded fallback.
        # 0.8 is the known hardcoded placeholder in model-service-1 app/model.py;
        # reject it so it cannot be misread as real evidence quality.
        confidence: float | None = None
        raw_conf = data.get("confidence")
        if isinstance(raw_conf, (int, float)) and raw_conf != 0.8:
            confidence = float(raw_conf)

        rationale = data.get("rationale")
        rationale_str = rationale.strip() if isinstance(rationale, str) and rationale.strip() else None

        matched = data.get("matched_keywords") or data.get("matched_signals")
        matched_signals = matched if isinstance(matched, list) else None

        dimensions.append(
            BehaviouralDimension(
                name=name,
                score=score_value,
                confidence=confidence,
                confidence_band=_confidence_band(confidence),
                rationale=rationale_str,
                matched_signals=matched_signals,
                source="service1",
            )
        )

    if not dimensions:
        raise InterviewScoringError("Culture fit model returned no scoreable dimensions.")

    # Weighted overall score using rubric weights (fall back to equal weighting)
    total_weight = 0.0
    weighted_sum = 0.0
    for dim in dimensions:
        weight = max(0.0, float(rubric.get(dim.name, 1.0)))
        total_weight += weight
        weighted_sum += dim.score * weight

    overall = (
        int(round(weighted_sum / total_weight))
        if total_weight > 0
        else int(round(sum(d.score for d in dimensions) / len(dimensions)))
    )

    # overall_alignment from model-service-1 is kept as a qualitative signal.
    # The authoritative recommendation is produced by compute_risk_stack() below.
    summary = model1_result.get("summary")
    summary_str = summary.strip() if isinstance(summary, str) and summary.strip() else None

    return CultureFitResult(
        overall_score=overall,
        overall_alignment=model1_result.get("overall_alignment"),
        overall_risk_level=model1_result.get("overall_risk_level"),
        # recommendation is intentionally left None here — it is set by
        # compute_risk_stack() after dimension classification runs.
        recommendation=None,
        dimensions=dimensions,
        dimension_outcomes=None,
        summary=summary_str,
    )


# ── Dimension classification (B2 + B3) ───────────────────────────────────────

def classify_dimensions(
    culture_fit: CultureFitResult,
    operating_environment: dict[str, Any],
) -> CultureFitResult:
    """
    Apply the backend's canonical env-adjusted threshold rule engine to classify
    each behavioural dimension as pass | watch | risk.

    This is the fix for B2 (dimension_outcomes never populated) and B3
    (compute_dimension_requirements() never called in the scoring path).

    The backend owns classification — model-service-1 is responsible only for
    producing scores. This keeps the rule engine in one place and ensures
    env-specific thresholds are always applied consistently.

    Confidence gating: dimensions with no confidence reading (None) are treated
    conservatively — they can be classified pass or watch but not risk, because
    there is no evidence of sufficient depth to justify a hard negative.
    """
    requirements = compute_dimension_requirements(operating_environment)

    classified_dimensions: list[BehaviouralDimension] = []
    dimension_outcomes: dict[str, DimensionOutcome] = {}

    for dim in culture_fit.dimensions:
        req = requirements.get(dim.name)
        if req is None:
            # Dimension not in the canonical rule set — carry through unclassified
            classified_dimensions.append(dim)
            continue

        score = dim.score
        pass_threshold = req.pass_threshold
        watch_threshold = req.watch_threshold

        # Determine raw classification from score vs env-adjusted thresholds
        if score >= pass_threshold:
            raw_outcome = "pass"
        elif score >= watch_threshold:
            raw_outcome = "watch"
        else:
            raw_outcome = "risk"

        # Confidence gate: a hard "risk" classification requires at least some
        # evidence confidence. If confidence is None (model didn't return it or
        # it was the hardcoded 0.8 placeholder), downgrade risk → watch.
        # This prevents a "risk" label from being applied with no evidence basis.
        if raw_outcome == "risk" and dim.confidence is None:
            raw_outcome = "watch"
            logger.debug(
                "Dimension %s downgraded risk→watch: no evidence-derived confidence",
                dim.name,
            )

        gap = score - pass_threshold
        outcome = DimensionOutcome(
            outcome=raw_outcome,
            required_pass=pass_threshold,
            required_watch=watch_threshold,
            gap=gap,
        )
        dimension_outcomes[dim.name] = outcome

        classified_dimensions.append(
            BehaviouralDimension(
                name=dim.name,
                score=dim.score,
                confidence=dim.confidence,
                confidence_band=dim.confidence_band,
                outcome=raw_outcome,
                required_pass=pass_threshold,
                required_watch=watch_threshold,
                gap=gap,
                rationale=dim.rationale,
                matched_signals=dim.matched_signals,
                source=dim.source,
            )
        )

    return CultureFitResult(
        overall_score=culture_fit.overall_score,
        overall_alignment=culture_fit.overall_alignment,
        overall_risk_level=culture_fit.overall_risk_level,
        recommendation=culture_fit.recommendation,
        dimensions=classified_dimensions,
        dimension_outcomes=dimension_outcomes if dimension_outcomes else None,
        summary=culture_fit.summary,
    )


# ── Risk stacking (B5) ────────────────────────────────────────────────────────

def compute_risk_stack(
    culture_fit: CultureFitResult,
    operating_environment: dict[str, Any],
    dimension_tiers: dict[str, str] | None = None,
) -> CultureFitResult:
    """
    Produce the authoritative hiring recommendation by counting dimension outcomes
    and applying the spec's risk-stacking rules.

    Rules (applied in order — first match wins):
      1. Fatal signal detected for this archetype → reject
      2. Critical dimension at risk → reject (importance tier escalation)
      3. Ambiguity risk AND Ownership risk together → reject (co-fail escalation)
      4. Effective risk count >= 2 → reject
         (Important dimension at risk counts as 2; Standard counts as 1)
      5. Effective risk count == 1 → caution
      6. 3 or more watch dimensions → caution
      7. 0 effective risks, fewer than 3 watches → proceed

    Environment confidence cap (applied after the above):
      If environment_confidence == "low" (derived from multi-respondent aggregation),
      the recommendation cannot be "proceed" — it is capped at "caution" because
      the operating environment thresholds themselves are unreliable.

    Importance tiers (dimension_tiers param):
      Standard  → risk contributes 1 to effective risk count (default)
      Important → risk contributes 2 to effective risk count
      Critical  → any risk immediately triggers reject (Rule 2)
    """
    tiers = dimension_tiers or {}
    outcomes = culture_fit.dimension_outcomes or {}

    risk_dims = [dim for dim, do in outcomes.items() if do.outcome == "risk"]
    watch_dims = [dim for dim, do in outcomes.items() if do.outcome == "watch"]

    # Compute effective risk count using importance tiers
    effective_risk_count = 0
    for dim in risk_dims:
        tier = tiers.get(dim, "Standard")
        if tier == "Important":
            effective_risk_count += 2
        else:
            effective_risk_count += 1

    # Rule 1: archetype fatal risk signals
    archetype = operating_environment.get("high_performance_archetype", "")
    fatal_signal_ids = set(get_archetype_fatal_risks(archetype))
    fatal_signals_matched: list[str] = []
    if fatal_signal_ids:
        for dim in culture_fit.dimensions:
            for sig in dim.matched_signals or []:
                if sig in fatal_signal_ids:
                    fatal_signals_matched.append(sig)

    if fatal_signals_matched:
        recommendation = "reject"
        overall_risk_level = "high"
        logger.info(
            "Risk stack: reject — fatal signals detected: %s", fatal_signals_matched
        )

    # Rule 2: Critical dimension at risk → immediate reject
    critical_risk_dims = [dim for dim in risk_dims if tiers.get(dim, "Standard") == "Critical"]
    if critical_risk_dims:
        recommendation = "reject"
        overall_risk_level = "high"
        logger.info(
            "Risk stack: reject — Critical dimension(s) at risk: %s", critical_risk_dims
        )

    # Rule 3: Ambiguity + Ownership co-fail
    elif "ambiguity" in risk_dims and "ownership" in risk_dims:
        recommendation = "reject"
        overall_risk_level = "high"
        logger.info("Risk stack: reject — ambiguity + ownership co-fail")

    # Rule 4: effective risk count >= 2
    elif effective_risk_count >= 2:
        recommendation = "reject"
        overall_risk_level = "high"
        logger.info(
            "Risk stack: reject — effective_risk_count=%d (dims=%s, tiers=%s)",
            effective_risk_count, risk_dims, {d: tiers.get(d, "Standard") for d in risk_dims},
        )

    # Rule 5: effective risk count == 1
    elif effective_risk_count == 1:
        recommendation = "caution"
        overall_risk_level = "medium"
        logger.info("Risk stack: caution — 1 effective risk: %s", risk_dims)

    # Rule 6: 3+ watch dimensions
    elif len(watch_dims) >= 3:
        recommendation = "caution"
        overall_risk_level = "medium"
        logger.info("Risk stack: caution — %d watch dimensions: %s", len(watch_dims), watch_dims)

    # Rule 7: clear
    else:
        recommendation = "proceed"
        overall_risk_level = "low" if not watch_dims else "medium"
        logger.info(
            "Risk stack: proceed — risks=%s watches=%s", risk_dims, watch_dims
        )

    # Environment confidence cap: low-confidence environment → cannot recommend "proceed"
    env_confidence = operating_environment.get("environment_confidence")
    if env_confidence == "low" and recommendation == "proceed":
        recommendation = "caution"
        overall_risk_level = "medium"
        logger.info(
            "Risk stack: proceed→caution (env confidence cap — environment_confidence=low)"
        )

    return CultureFitResult(
        overall_score=culture_fit.overall_score,
        overall_alignment=culture_fit.overall_alignment,
        overall_risk_level=overall_risk_level,
        recommendation=recommendation,
        dimensions=culture_fit.dimensions,
        dimension_outcomes=culture_fit.dimension_outcomes,
        summary=culture_fit.summary,
    )


# ── Skills fit extraction ─────────────────────────────────────────────────────

def _extract_skills_fit(model2_result: dict[str, Any]) -> SkillsFitResult | None:
    """
    Extract the skills fit scorecard from model-service-2's response.

    Model-service-2 scores the candidate's demonstrated skills against the
    specific competencies required by the job description and resume. Skill names
    are role-specific (e.g. python, azure, rag) — not the canonical behavioural
    dimensions. This scorecard is entirely independent of the culture fit result.

    Returns None if model-service-2 failed or returned no usable data.
    """
    if not isinstance(model2_result, dict):
        return None

    if model2_result.get("error"):
        logger.warning("Skills model failed: %s", model2_result.get("error"))
        return None

    scores_raw = model2_result.get("scores")
    if not isinstance(scores_raw, dict) or not scores_raw:
        logger.warning("Skills model returned no skill scores.")
        return None

    skills: dict[str, SkillScore] = {}
    for skill_name, data in scores_raw.items():
        if not isinstance(skill_name, str) or not isinstance(data, dict):
            continue
        raw_score = data.get("score")
        if raw_score is None:
            continue
        try:
            score_f = float(raw_score)
            # Model-service-2 returns 0-1 scores
            if 0.0 <= score_f <= 1.0:
                score_f *= 100.0
            score_int = max(0, min(100, int(round(score_f))))
        except (TypeError, ValueError):
            continue

        raw_conf = data.get("confidence")
        confidence = float(raw_conf) if isinstance(raw_conf, (int, float)) else None

        keywords = data.get("matched_keywords")

        skills[skill_name] = SkillScore(
            score=score_int,
            confidence=confidence,
            rationale=data.get("rationale"),
            years_detected=data.get("years_detected"),
            matched_keywords=keywords if isinstance(keywords, list) else None,
        )

    if not skills:
        return None

    overall_raw = model2_result.get("overall_score", 0)
    try:
        overall = max(0, min(100, int(round(float(overall_raw)))))
    except (TypeError, ValueError):
        overall = int(round(sum(s.score for s in skills.values()) / len(skills)))

    summary = model2_result.get("summary")

    return SkillsFitResult(
        overall_score=overall,
        outcome=model2_result.get("outcome"),
        skills=skills,
        must_haves_passed=model2_result.get("must_haves_passed") or [],
        must_haves_failed=model2_result.get("must_haves_failed") or [],
        gaps=model2_result.get("gaps") or [],
        summary=summary.strip() if isinstance(summary, str) and summary.strip() else None,
    )


# ── Persistence ───────────────────────────────────────────────────────────────

def persist_interview_score(
    db: Session,
    *,
    interview_id: str,
    culture_fit: CultureFitResult,
    skills_fit: SkillsFitResult | None = None,
    env_snapshot: dict[str, Any] | None = None,
    model_version: str | None = None,
    service1_raw: dict[str, Any] | None = None,
    service2_raw: dict[str, Any] | None = None,
) -> InterviewScore:
    """
    Persist the dual scorecard to the database.

    Culture fit dimensions are written to score_dimensions (one row per canonical
    dimension, with env-adjusted thresholds and pass/watch/risk outcome).
    Skills fit is summarised in interview_scores and preserved in full in service2_raw.
    """
    dim_outcomes_json: str | None = None
    if culture_fit.dimension_outcomes:
        dim_outcomes_json = json.dumps({
            dim: {
                "outcome": do.outcome,
                "required_pass": do.required_pass,
                "required_watch": do.required_watch,
                "gap": do.gap,
            }
            for dim, do in culture_fit.dimension_outcomes.items()
        })

    score = db.query(InterviewScore).filter(
        InterviewScore.interview_id == interview_id
    ).first()

    common_fields: dict[str, Any] = dict(
        culture_fit_score=culture_fit.overall_score,
        skills_score=skills_fit.overall_score if skills_fit else None,
        skills_outcome=skills_fit.outcome if skills_fit else None,
        summary=culture_fit.summary,
        overall_alignment=culture_fit.overall_alignment,
        overall_risk_level=culture_fit.overall_risk_level,
        recommendation=culture_fit.recommendation,
        dimension_outcomes=dim_outcomes_json,
        env_snapshot=json.dumps(env_snapshot) if env_snapshot else None,
        model_version=model_version,
        service1_raw=json.dumps(service1_raw) if service1_raw else None,
        service2_raw=json.dumps(service2_raw) if service2_raw else None,
    )

    if score:
        for k, v in common_fields.items():
            setattr(score, k, v)
    else:
        score = InterviewScore(
            interview_id=interview_id,
            created_at=datetime.utcnow(),
            **common_fields,
        )
        db.add(score)

    # Replace canonical dimension rows
    db.query(ScoreDimension).filter(
        ScoreDimension.interview_id == interview_id
    ).delete()

    for dim in culture_fit.dimensions:
        outcome_data = (culture_fit.dimension_outcomes or {}).get(dim.name)
        db.add(
            ScoreDimension(
                interview_id=interview_id,
                name=dim.name,
                score=dim.score,
                rationale=dim.rationale,
                confidence=dim.confidence,
                outcome=outcome_data.outcome if outcome_data else None,
                required_pass=outcome_data.required_pass if outcome_data else None,
                required_watch=outcome_data.required_watch if outcome_data else None,
                gap=outcome_data.gap if outcome_data else None,
                matched_signals=json.dumps(dim.matched_signals) if dim.matched_signals else None,
                source=dim.source,
                created_at=datetime.utcnow(),
            )
        )

    return score


# ── Auto-scoring pipeline ─────────────────────────────────────────────────────

async def run_auto_scoring_for_interview(
    db: Session, interview_id: str
) -> dict[str, Any]:
    interview = db.get(Interview, interview_id)
    if not interview:
        raise InterviewScoringError("Interview not found")

    transcript_rows = (
        db.query(TranscriptSegment)
        .filter(TranscriptSegment.interview_id == interview_id)
        .order_by(TranscriptSegment.sequence.asc())
        .all()
    )
    if not transcript_rows:
        raise InterviewScoringError("Transcript required for scoring")

    transcript = [
        {"speaker": row.speaker, "content": row.content}
        for row in transcript_rows
    ]

    application = db.get(Application, interview.application_id)
    if not application:
        raise InterviewScoringError("Interview application not found")

    job_role = db.get(JobRole, application.job_role_id)
    organisation = db.get(Organisation, job_role.organisation_id) if job_role else None
    if not job_role or not organisation:
        raise InterviewScoringError("Interview context is incomplete")

    try:
        operating_environment, taxonomy = load_org_culture_context(organisation)
    except CultureContextError as exc:
        raise InterviewScoringError(str(exc)) from exc

    rubric: dict[str, float] = {}
    dimension_tiers: dict[str, str] = {}
    if job_role.scoring_rubric:
        try:
            parsed_rubric = json.loads(job_role.scoring_rubric)
            if isinstance(parsed_rubric, dict):
                rubric, dimension_tiers = _parse_rubric(parsed_rubric)
        except json.JSONDecodeError:
            pass

    try:
        model1_result, model2_result = await ml_client.get_combined_predictions(
            transcript,
            job_description=job_role.description or "",
            resume_text="",
            role_title=job_role.title,
            seniority=None,
            candidate_id=application.candidate_profile_id,
            role_id=job_role.id,
            department_id=job_role.department,
            interview_id=interview.id,
            operating_environment=operating_environment,
            taxonomy=taxonomy,
            trace=False,
        )
    except MLServiceError as exc:
        raise InterviewScoringError(str(exc)) from exc

    # Step 1: extract scores from model-service-1
    culture_fit = _extract_culture_fit(model1_result, rubric=rubric)

    # Step 2: classify each dimension using the backend's env-adjusted rule engine
    culture_fit = classify_dimensions(culture_fit, operating_environment)

    # Step 3: derive the final recommendation from risk-count stacking
    culture_fit = compute_risk_stack(culture_fit, operating_environment, dimension_tiers=dimension_tiers)

    # Shadow TDS integration point: behavioural evidence is normalized and the
    # org/role/interview context is available, but no public response or skills
    # handling has been touched yet. This keeps MVP1 "behaviour decides" dark.
    _maybe_run_shadow_behavioural_decision_write(
        db,
        interview_id=interview_id,
        candidate_id=application.candidate_profile_id,
        role_id=job_role.id,
        organisation_id=organisation.id,
        operating_environment=operating_environment,
        culture_fit=culture_fit,
        dimension_tiers=dimension_tiers,
    )

    # Step 4: extract skills scorecard independently
    skills_fit = _extract_skills_fit(model2_result)

    persist_interview_score(
        db,
        interview_id=interview_id,
        culture_fit=culture_fit,
        skills_fit=skills_fit,
        env_snapshot=operating_environment,
        model_version=model1_result.get("model_version"),
        service1_raw=model1_result,
        service2_raw=model2_result,
    )

    _maybe_run_shadow_skills_assessment_summary_write(
        db,
        interview_id=interview_id,
        candidate_id=application.candidate_profile_id,
        role_id=job_role.id,
        organisation_id=organisation.id,
        model2_result=model2_result,
    )

    interview.summary = culture_fit.summary
    interview.updated_at = datetime.utcnow()

    return {
        "interview_id": interview_id,
        "culture_fit_score": culture_fit.overall_score,
        "skills_score": skills_fit.overall_score if skills_fit else None,
        "skills_outcome": skills_fit.outcome if skills_fit else None,
        "recommendation": culture_fit.recommendation,
        "overall_alignment": culture_fit.overall_alignment,
        "overall_risk_level": culture_fit.overall_risk_level,
        "dimension_count": len(culture_fit.dimensions),
    }
