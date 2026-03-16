from __future__ import annotations

import logging
from datetime import datetime
import json
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


class InterviewScoringError(RuntimeError):
    pass


def _collect_dimensions(result: dict[str, Any], source: str) -> tuple[list[ScoringDimension], list[str]]:
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
            raw_score = float(data.get("score"))
            if 0.0 <= raw_score <= 1.0:
                raw_score *= 100.0
            score_value = int(round(raw_score))
        except (TypeError, ValueError):
            notes.append(f"{source} returned invalid score value for {name or 'unknown'}.")
            continue

        rationale = data.get("rationale")
        if isinstance(rationale, str) and rationale.strip():
            rationale = f"{source}: {rationale.strip()}"
        else:
            rationale = f"{source} score."

        dimensions.append(
            ScoringDimension(
                name=name,
                score=max(0, min(100, score_value)),
                rationale=rationale,
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
) -> tuple[int, list[ScoringDimension], str]:
    rubric = rubric or {}
    model1_dimensions, model1_notes = _collect_dimensions(model1_result, "Culture model")
    model2_dimensions, model2_notes = _collect_dimensions(model2_result, "Skillset model")

    dimension_scores: dict[str, list[int]] = {}
    dimension_rationales: dict[str, list[str]] = {}
    for dimension in model1_dimensions + model2_dimensions:
        dimension_scores.setdefault(dimension.name, []).append(dimension.score)
        if dimension.rationale:
            dimension_rationales.setdefault(dimension.name, []).append(dimension.rationale)

    if not dimension_scores:
        raise InterviewScoringError("No model scores returned.")

    dimensions: list[ScoringDimension] = []
    for name in sorted(dimension_scores):
        scores = dimension_scores[name]
        weight = float(rubric.get(name, 1.0))
        rationale = "; ".join(dimension_rationales.get(name, [])) or None
        dimensions.append(
            ScoringDimension(
                name=name,
                score=int(round(sum(scores) / max(1, len(scores)))),
                rationale=rationale,
            )
        )

    total_weight = 0.0
    weighted_sum = 0.0
    for dimension in dimensions:
        weight = float(rubric.get(dimension.name, 1.0))
        if weight < 0:
            weight = 0.0
        total_weight += weight
        weighted_sum += dimension.score * weight

    overall = (
        int(round(weighted_sum / total_weight))
        if total_weight > 0
        else int(round(sum(d.score for d in dimensions) / len(dimensions)))
    )
    summary = " ".join(model1_notes + model2_notes).strip() or "Automated scoring from model services."
    return overall, dimensions, summary


def persist_interview_score(
    db: Session,
    *,
    interview_id: str,
    overall_score: int,
    dimensions: list[ScoringDimension],
    summary: str,
) -> InterviewScore:
    score = db.query(InterviewScore).filter(InterviewScore.interview_id == interview_id).first()
    if score:
        score.overall_score = overall_score
        score.summary = summary
    else:
        score = InterviewScore(
            interview_id=interview_id,
            overall_score=overall_score,
            summary=summary,
            created_at=datetime.utcnow(),
        )
        db.add(score)

    db.query(ScoreDimension).filter(ScoreDimension.interview_id == interview_id).delete()
    for dimension in dimensions:
        db.add(
            ScoreDimension(
                interview_id=interview_id,
                name=dimension.name,
                score=dimension.score,
                rationale=dimension.rationale,
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
        except json.JSONDecodeError:
            parsed_rubric = {}
        if isinstance(parsed_rubric, dict):
            rubric = parsed_rubric
    model1_result: dict[str, Any]
    model2_result: dict[str, Any]
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

    overall, dimensions, summary = _merge_scores(model1_result, model2_result, rubric=rubric)
    persist_interview_score(
        db,
        interview_id=interview_id,
        overall_score=overall,
        dimensions=dimensions,
        summary=summary,
    )
    interview.summary = summary
    interview.updated_at = datetime.utcnow()
    return {
        "interview_id": interview_id,
        "overall_score": overall,
        "dimension_count": len(dimensions),
    }
