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
from app.schemas.scoring import ScoringDimension
from app.services.culture_fit import CultureContextError, load_org_culture_context
from app.services.ml_client import MLServiceError, ml_client

logger = logging.getLogger(__name__)

CANONICAL_DIMENSIONS = ["ownership", "execution", "challenge", "ambiguity", "feedback"]


class InterviewScoringError(RuntimeError):
    pass


def _collect_dimensions(
    result: dict[str, Any],
    source: str,
) -> tuple[list[ScoringDimension], list[str]]:
    """Extract per-dimension scores from a model service result dict."""
    dimensions: list[ScoringDimension] = []
    notes: list[str] = []
    if not isinstance(result, dict):
        notes.append(f"{source} returned an invalid response.")
        return dimensions, notes

    if result.get("error"):
        notes.append(f"{source} failed: {result.get('error')}")
        return dimensions, notes

    scores = result.get("scores")
    if not isinstance(scores, dict):
        notes.append(f"{source} returned no scores.")
        return dimensions, notes

    for name, data in scores.items():
        if not isinstance(name, str) or not name.strip() or not isinstance(data, dict) or "score" not in data:
            notes.append(f"{source} returned invalid score payload for {name or 'unknown'}.")
            continue
        try:
            raw_score = float(data["score"])
            if 0.0 <= raw_score <= 1.0:
                raw_score *= 100.0
            score_value = max(0, min(100, int(round(raw_score))))
        except (TypeError, ValueError):
            notes.append(f"{source} returned invalid score value for {name}.")
            continue

        rationale = data.get("rationale")
        rationale_str = f"{source}: {rationale.strip()}" if isinstance(rationale, str) and rationale.strip() else f"{source} score."

        # Confidence — independent of score, from evidence quality
        confidence: float | None = None
        raw_confidence = data.get("confidence")
        if isinstance(raw_confidence, (int, float)):
            confidence = float(raw_confidence)

        matched_signals = data.get("matched_keywords") or data.get("matched_signals")
        if not isinstance(matched_signals, list):
            matched_signals = None

        dimensions.append(
            ScoringDimension(
                name=name,
                score=score_value,
                rationale=rationale_str,
                confidence=confidence,
                matched_signals=matched_signals,
                source=source,
            )
        )

    summary = result.get("summary")
    if isinstance(summary, str) and summary.strip():
        notes.append(f"{source} summary: {summary.strip()}")

    return dimensions, notes


def _merge_scores(
    model1_result: dict[str, Any],
    model2_result: dict[str, Any],
    rubric: dict[str, float] | None = None,
) -> tuple[int, list[ScoringDimension], str, dict[str, Any]]:
    """
    Merge per-dimension scores from both model services.

    Returns (overall_score, merged_dimensions, summary, decision_fields).
    decision_fields contains: overall_alignment, overall_risk_level, recommendation,
    dimension_outcomes, env_requirements extracted from model1_result.
    """
    rubric = rubric or {}
    model1_dimensions, model1_notes = _collect_dimensions(model1_result, "service1")
    model2_dimensions, model2_notes = _collect_dimensions(model2_result, "service2")

    # For each canonical dimension, average scores across services
    dimension_score_lists: dict[str, list[int]] = {}
    dimension_confidence_lists: dict[str, list[float]] = {}
    dimension_rationales: dict[str, list[str]] = {}
    dimension_signals: dict[str, list[str]] = {}

    for dim in model1_dimensions + model2_dimensions:
        dimension_score_lists.setdefault(dim.name, []).append(dim.score)
        if dim.confidence is not None:
            dimension_confidence_lists.setdefault(dim.name, []).append(dim.confidence)
        if dim.rationale:
            dimension_rationales.setdefault(dim.name, []).append(dim.rationale)
        if dim.matched_signals:
            dimension_signals.setdefault(dim.name, []).extend(dim.matched_signals)

    if not dimension_score_lists:
        raise InterviewScoringError("No model scores returned.")

    # Dimension outcomes from model-service-1 (env-matched pass/watch/risk)
    m1_dimension_outcomes: dict[str, Any] = {}
    raw_outcomes = model1_result.get("dimension_outcomes")
    if isinstance(raw_outcomes, dict):
        m1_dimension_outcomes = raw_outcomes

    merged_dimensions: list[ScoringDimension] = []
    for name in sorted(dimension_score_lists.keys()):
        scores = dimension_score_lists[name]
        avg_score = int(round(sum(scores) / len(scores)))

        conf_list = dimension_confidence_lists.get(name, [])
        avg_confidence = round(sum(conf_list) / len(conf_list), 3) if conf_list else None

        rationale = "; ".join(dimension_rationales.get(name, [])) or None
        signals = list(dict.fromkeys(dimension_signals.get(name, [])))  # deduplicated

        outcome_data = m1_dimension_outcomes.get(name, {})

        merged_dimensions.append(
            ScoringDimension(
                name=name,
                score=avg_score,
                rationale=rationale,
                confidence=avg_confidence,
                outcome=outcome_data.get("outcome"),
                required_pass=outcome_data.get("required_pass"),
                required_watch=outcome_data.get("required_watch"),
                gap=outcome_data.get("gap"),
                matched_signals=signals or None,
                source="merged",
            )
        )

    # Weighted overall score
    total_weight = 0.0
    weighted_sum = 0.0
    for dim in merged_dimensions:
        weight = max(0.0, float(rubric.get(dim.name, 1.0)))
        total_weight += weight
        weighted_sum += dim.score * weight

    overall = (
        int(round(weighted_sum / total_weight))
        if total_weight > 0
        else int(round(sum(d.score for d in merged_dimensions) / len(merged_dimensions)))
    )

    summary = " ".join(model1_notes + model2_notes).strip() or "Automated scoring from model services."

    # Pass through decision-dominant fields from model-service-1
    decision_fields: dict[str, Any] = {
        "overall_alignment": model1_result.get("overall_alignment"),
        "overall_risk_level": model1_result.get("overall_risk_level"),
        "recommendation": model1_result.get("recommendation"),
        "dimension_outcomes": m1_dimension_outcomes,
        "model_version": model1_result.get("model_version"),
    }

    return overall, merged_dimensions, summary, decision_fields


def persist_interview_score(
    db: Session,
    *,
    interview_id: str,
    overall_score: int,
    dimensions: list[ScoringDimension],
    summary: str,
    overall_alignment: str | None = None,
    overall_risk_level: str | None = None,
    recommendation: str | None = None,
    dimension_outcomes: dict[str, Any] | None = None,
    env_snapshot: dict[str, Any] | None = None,
    model_version: str | None = None,
    service1_raw: dict[str, Any] | None = None,
    service2_raw: dict[str, Any] | None = None,
) -> InterviewScore:
    score = db.query(InterviewScore).filter(InterviewScore.interview_id == interview_id).first()
    if score:
        score.overall_score = overall_score
        score.summary = summary
        score.overall_alignment = overall_alignment
        score.overall_risk_level = overall_risk_level
        score.recommendation = recommendation
        score.dimension_outcomes = json.dumps(dimension_outcomes) if dimension_outcomes else None
        score.env_snapshot = json.dumps(env_snapshot) if env_snapshot else None
        score.model_version = model_version
        score.service1_raw = json.dumps(service1_raw) if service1_raw else None
        score.service2_raw = json.dumps(service2_raw) if service2_raw else None
    else:
        score = InterviewScore(
            interview_id=interview_id,
            overall_score=overall_score,
            summary=summary,
            overall_alignment=overall_alignment,
            overall_risk_level=overall_risk_level,
            recommendation=recommendation,
            dimension_outcomes=json.dumps(dimension_outcomes) if dimension_outcomes else None,
            env_snapshot=json.dumps(env_snapshot) if env_snapshot else None,
            model_version=model_version,
            service1_raw=json.dumps(service1_raw) if service1_raw else None,
            service2_raw=json.dumps(service2_raw) if service2_raw else None,
            created_at=datetime.utcnow(),
        )
        db.add(score)

    # Replace dimension rows
    db.query(ScoreDimension).filter(ScoreDimension.interview_id == interview_id).delete()
    for dim in dimensions:
        db.add(
            ScoreDimension(
                interview_id=interview_id,
                name=dim.name,
                score=dim.score,
                rationale=dim.rationale,
                confidence=dim.confidence,
                outcome=dim.outcome,
                required_pass=dim.required_pass,
                required_watch=dim.required_watch,
                gap=dim.gap,
                matched_signals=json.dumps(dim.matched_signals) if dim.matched_signals else None,
                source=dim.source,
                created_at=datetime.utcnow(),
            )
        )
    return score


async def run_auto_scoring_for_interview(db: Session, interview_id: str) -> dict[str, Any]:
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

    transcript = [{"speaker": row.speaker, "content": row.content} for row in transcript_rows]
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

    overall, dimensions, summary, decision_fields = _merge_scores(
        model1_result, model2_result, rubric=rubric
    )

    persist_interview_score(
        db,
        interview_id=interview_id,
        overall_score=overall,
        dimensions=dimensions,
        summary=summary,
        overall_alignment=decision_fields.get("overall_alignment"),
        overall_risk_level=decision_fields.get("overall_risk_level"),
        recommendation=decision_fields.get("recommendation"),
        dimension_outcomes=decision_fields.get("dimension_outcomes"),
        env_snapshot=operating_environment,
        model_version=decision_fields.get("model_version"),
        service1_raw=model1_result,
        service2_raw=model2_result,
    )
    interview.summary = summary
    interview.updated_at = datetime.utcnow()
    return {
        "interview_id": interview_id,
        "overall_score": overall,
        "recommendation": decision_fields.get("recommendation"),
        "overall_alignment": decision_fields.get("overall_alignment"),
        "overall_risk_level": decision_fields.get("overall_risk_level"),
        "dimension_count": len(dimensions),
    }
