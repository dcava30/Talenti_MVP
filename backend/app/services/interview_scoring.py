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

logger = logging.getLogger(__name__)

CANONICAL_DIMENSIONS = ["ownership", "execution", "challenge", "ambiguity", "feedback"]


class InterviewScoringError(RuntimeError):
    pass


# ── Culture fit extraction ────────────────────────────────────────────────────

def _extract_culture_fit(
    model1_result: dict[str, Any],
    rubric: dict[str, float] | None = None,
) -> CultureFitResult:
    """
    Extract the culture fit scorecard from model-service-1's response.

    Model-service-1 scores the 5 canonical behavioural dimensions (ownership,
    execution, challenge, ambiguity, feedback) against the org's operating
    environment. Its output is self-contained — no merging with skills data.
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

        # Evidence-derived confidence — do NOT use a hardcoded fallback value.
        # If the model doesn't return confidence, leave it as None so that downstream
        # logic cannot misinterpret a fake confidence as evidence quality.
        confidence: float | None = None
        raw_conf = data.get("confidence")
        if isinstance(raw_conf, (int, float)) and raw_conf != 0.8:
            # 0.8 is the known hardcoded placeholder in model-service-1 app/model.py.
            # Reject it — it is not evidence-derived.
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

    # Dimension outcomes (pass/watch/risk) from model-service-1 if present
    raw_outcomes = model1_result.get("dimension_outcomes")
    dimension_outcomes: dict[str, DimensionOutcome] | None = None
    if isinstance(raw_outcomes, dict) and raw_outcomes:
        dimension_outcomes = {}
        for dim, data in raw_outcomes.items():
            if isinstance(data, dict):
                dimension_outcomes[dim] = DimensionOutcome(
                    outcome=data.get("outcome", "risk"),
                    required_pass=data.get("required_pass", 0),
                    required_watch=data.get("required_watch", 0),
                    gap=data.get("gap", 0),
                )

    summary = model1_result.get("summary")
    summary_str = summary.strip() if isinstance(summary, str) and summary.strip() else None

    return CultureFitResult(
        overall_score=overall,
        overall_alignment=model1_result.get("overall_alignment"),
        overall_risk_level=model1_result.get("overall_risk_level"),
        recommendation=model1_result.get("recommendation"),
        dimensions=dimensions,
        dimension_outcomes=dimension_outcomes,
        summary=summary_str,
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
    dimension). Skills fit is summarised in interview_scores (overall score +
    outcome) and preserved in full in service2_raw.
    """
    # Build dimension_outcomes JSON from culture fit result
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

    # Replace canonical dimension rows (culture fit only — skills are in service2_raw)
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

    # Extract each scorecard independently — they are not merged
    culture_fit = _extract_culture_fit(model1_result, rubric=rubric)
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
