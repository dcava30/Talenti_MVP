from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import (
    Application,
    Interview,
    InterviewScore,
    JobRole,
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
from app.services.culture_fit import CultureContextError, load_org_culture_context
from app.services.ml_client import MLServiceError, ml_client
from app.talenti_canonical.dimensions import (
    compute_dimension_requirements,
    get_archetype_fatal_risks,
)

logger = logging.getLogger(__name__)

CANONICAL_DIMENSIONS = ["ownership", "execution", "challenge", "ambiguity", "feedback"]


class InterviewScoringError(RuntimeError):
    pass


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
) -> CultureFitResult:
    """
    Produce the authoritative hiring recommendation by counting dimension outcomes
    and applying the spec's risk-stacking rules.

    Rules (applied in order — first match wins):
      1. Fatal signal detected for this archetype → reject
      2. Ambiguity risk AND Ownership risk together → reject (co-fail escalation)
      3. 2 or more risk dimensions → reject
      4. 1 risk dimension → caution
      5. 3 or more watch dimensions → caution
      6. 0 risk dimensions, fewer than 3 watches → proceed

    Environment confidence cap (applied after the above):
      If environment_confidence == "low" (derived from multi-respondent aggregation),
      the recommendation cannot be "proceed" — it is capped at "caution" because
      the operating environment thresholds themselves are unreliable.

    The overall_risk_level is also derived here from dimension outcomes rather
    than from the model's internal weighted-score threshold.
    """
    outcomes = culture_fit.dimension_outcomes or {}

    risk_dims = [dim for dim, do in outcomes.items() if do.outcome == "risk"]
    watch_dims = [dim for dim, do in outcomes.items() if do.outcome == "watch"]

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

    # Rule 2: Ambiguity + Ownership co-fail
    elif "ambiguity" in risk_dims and "ownership" in risk_dims:
        recommendation = "reject"
        overall_risk_level = "high"
        logger.info("Risk stack: reject — ambiguity + ownership co-fail")

    # Rule 3: 2+ risk dimensions
    elif len(risk_dims) >= 2:
        recommendation = "reject"
        overall_risk_level = "high"
        logger.info("Risk stack: reject — %d risk dimensions: %s", len(risk_dims), risk_dims)

    # Rule 4: exactly 1 risk dimension
    elif len(risk_dims) == 1:
        recommendation = "caution"
        overall_risk_level = "medium"
        logger.info("Risk stack: caution — 1 risk dimension: %s", risk_dims)

    # Rule 5: 3+ watch dimensions
    elif len(watch_dims) >= 3:
        recommendation = "caution"
        overall_risk_level = "medium"
        logger.info("Risk stack: caution — %d watch dimensions: %s", len(watch_dims), watch_dims)

    # Rule 6: clear
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
    if job_role.scoring_rubric:
        try:
            parsed_rubric = json.loads(job_role.scoring_rubric)
            if isinstance(parsed_rubric, dict):
                rubric = parsed_rubric
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
    culture_fit = compute_risk_stack(culture_fit, operating_environment)

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
