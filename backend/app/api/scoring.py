import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_org_member
from app.models import Application, Interview, JobRole, Organisation, User
from app.schemas.scoring import ScoringDimension, ScoringRequest, ScoringResponse
from app.services.culture_fit import CultureContextError, load_org_culture_context
from app.services.ml_client import MLServiceError, ml_client

router = APIRouter(prefix="/api/v1/scoring", tags=["scoring"])
logger = logging.getLogger(__name__)


@router.post("/analyze", response_model=ScoringResponse)
async def score_interview(
    payload: ScoringRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ScoringResponse:
    if not payload.transcript:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Transcript required")

    try:
        transcript_data = []
        for idx, segment in enumerate(payload.transcript):
            assert segment.speaker is not None, f"Transcript segment {idx} missing speaker"
            assert segment.content is not None, f"Transcript segment {idx} missing content"
            transcript_data.append({"speaker": str(segment.speaker), "content": str(segment.content)})
        assert transcript_data, "Transcript normalization produced no segments"
    except AssertionError as exc:
        logger.error("Invalid transcript payload: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid transcript: {exc}",
        ) from exc
    except Exception as exc:
        logger.error("Failed to normalize transcript payload: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process transcript",
        ) from exc

    operating_environment: dict | None = None
    taxonomy: dict | None = None
    candidate_id: str | None = None
    resolved_org_id = payload.org_id
    resolved_role_id = payload.role_id
    resolved_department_id = payload.department_id
    resolved_application_id = payload.application_id

    if payload.operating_environment or payload.taxonomy:
        if not payload.operating_environment or not payload.taxonomy:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Both operating_environment and taxonomy are required for fit scoring.",
            )
        operating_environment = payload.operating_environment.model_dump()
        taxonomy = payload.taxonomy.model_dump()
    else:
        interview = db.get(Interview, payload.interview_id) if payload.interview_id else None
        if interview:
            resolved_application_id = resolved_application_id or interview.application_id

        application = db.get(Application, resolved_application_id) if resolved_application_id else None
        if application:
            resolved_role_id = resolved_role_id or application.job_role_id
            candidate_id = application.candidate_profile_id

        job_role = db.get(JobRole, resolved_role_id) if resolved_role_id else None
        if job_role:
            resolved_org_id = resolved_org_id or job_role.organisation_id
            resolved_department_id = resolved_department_id or job_role.department

        if not resolved_org_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organisation context is required for culture fit scoring.",
            )

        require_org_member(resolved_org_id, db, user)
        organisation = db.get(Organisation, resolved_org_id)
        if not organisation:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found")
        try:
            operating_environment, taxonomy = load_org_culture_context(organisation)
        except CultureContextError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc

    if not operating_environment or not taxonomy:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organisation operating_environment and taxonomy are required for culture fit scoring.",
        )

    try:
        model1_result, model2_result = await ml_client.get_combined_predictions(
            transcript_data,
            job_description=payload.job_description or "",
            resume_text=payload.resume_text or "",
            role_title=payload.role_title,
            seniority=payload.seniority,
            candidate_id=candidate_id,
            role_id=resolved_role_id,
            department_id=resolved_department_id,
            interview_id=payload.interview_id,
            operating_environment=operating_environment,
            taxonomy=taxonomy,
            trace=payload.trace,
        )
    except MLServiceError as exc:
        logger.error("ML service error while scoring: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except AssertionError as exc:
        logger.error("Assertion failed while requesting model predictions: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Invalid model request: {exc}",
        ) from exc
    except Exception as exc:
        logger.error("Unexpected error while requesting model predictions: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unexpected error while calling model services.",
        ) from exc

    try:
        assert isinstance(model1_result, dict), "Culture model response was not a JSON object"
        assert isinstance(model2_result, dict), "Skillset model response was not a JSON object"
    except AssertionError as exc:
        logger.error("Model response validation failed: %s", exc)
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
            try:
                assert isinstance(name, str) and name.strip(), "Invalid dimension name"
                assert isinstance(data, dict), f"Invalid score payload for {name}"
                assert "score" in data, f"Missing score for {name}"
                score_value = int(round(float(data.get("score"))))
            except AssertionError as exc:
                logger.warning("%s invalid score payload: %s", source, exc)
                notes.append(f"{source} returned invalid score payload for {name or 'unknown'}.")
                continue
            except (TypeError, ValueError) as exc:
                logger.warning("%s invalid score value for %s: %s", source, name, exc)
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

    model1_dimensions, model1_notes = collect_dimensions(model1_result, "Culture model")
    model2_dimensions, model2_notes = collect_dimensions(model2_result, "Skillset model")

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
    try:
        assert isinstance(rubric, dict), "Rubric must be a dictionary of weights"
    except AssertionError as exc:
        logger.error("Invalid rubric payload: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    total_weight = 0.0
    weighted_sum = 0.0
    try:
        for dimension in dimensions:
            assert 0 <= dimension.score <= 100, f"Dimension score out of range for {dimension.name}"
            weight = rubric.get(dimension.name, 1.0)
            try:
                weight_value = float(weight)
            except (TypeError, ValueError):
                weight_value = 1.0
            if weight_value < 0:
                weight_value = 0.0
            total_weight += weight_value
            weighted_sum += dimension.score * weight_value
    except AssertionError as exc:
        logger.error("Invalid dimension score during weighting: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Invalid dimension score: {exc}",
        ) from exc
    except Exception as exc:
        logger.error("Failed to compute weighted score: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compute weighted score.",
        ) from exc

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
