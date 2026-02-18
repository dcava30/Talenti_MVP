from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import User
from app.schemas.scoring import ScoringDimension, ScoringRequest, ScoringResponse
from app.services.ml_client import MLServiceError, ml_client

router = APIRouter(prefix="/api/v1/scoring", tags=["scoring"])


@router.post("/analyze", response_model=ScoringResponse)
async def score_interview(
    payload: ScoringRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ScoringResponse:
    if not payload.transcript:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Transcript required")

    transcript_data = [
        {"speaker": segment.speaker, "content": segment.content}
        for segment in payload.transcript
    ]

    try:
        model1_result, model2_result = await ml_client.get_combined_predictions(
            transcript_data,
            job_description=payload.job_description or "",
            resume_text=payload.resume_text or "",
            role_title=payload.role_title,
            seniority=payload.seniority,
        )
    except MLServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    def collect_dimensions(result: dict, source: str) -> tuple[list[ScoringDimension], list[str]]:
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
            if not isinstance(data, dict) or "score" not in data:
                continue
            try:
                score_value = int(round(float(data.get("score"))))
            except (TypeError, ValueError):
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

    model1_dimensions, model1_notes = collect_dimensions(model1_result, "Model service 1")
    model2_dimensions, model2_notes = collect_dimensions(model2_result, "Model service 2")

    dimension_scores: dict[str, list[int]] = {}
    dimension_rationales: dict[str, list[str]] = {}

    for dimension in model1_dimensions + model2_dimensions:
        dimension_scores.setdefault(dimension.name, []).append(dimension.score)
        if dimension.rationale:
            dimension_rationales.setdefault(dimension.name, []).append(dimension.rationale)

    if not dimension_scores:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="No model scores returned.",
        )

    dimensions: list[ScoringDimension] = []
    for name in sorted(dimension_scores.keys()):
        scores = dimension_scores[name]
        average_score = int(round(sum(scores) / max(1, len(scores))))
        rationale_parts = dimension_rationales.get(name, [])
        rationale = "; ".join(rationale_parts) if rationale_parts else None
        dimensions.append(
            ScoringDimension(
                name=name,
                score=average_score,
                rationale=rationale,
            )
        )

    rubric = payload.rubric or {}
    total_weight = 0.0
    weighted_sum = 0.0
    for dimension in dimensions:
        weight = rubric.get(dimension.name, 1.0)
        try:
            weight_value = float(weight)
        except (TypeError, ValueError):
            weight_value = 1.0
        if weight_value < 0:
            weight_value = 0.0
        total_weight += weight_value
        weighted_sum += dimension.score * weight_value

    if total_weight <= 0:
        overall = int(round(sum(d.score for d in dimensions) / len(dimensions)))
    else:
        overall = int(round(weighted_sum / total_weight))

    summary_notes = model1_notes + model2_notes
    summary = " ".join(summary_notes).strip() or "Automated scoring from model services."
    return ScoringResponse(
        interview_id=payload.interview_id,
        overall_score=overall,
        dimensions=dimensions,
        summary=summary,
    )
