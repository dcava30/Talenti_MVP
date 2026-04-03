import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_org_member
from app.models import Application, Interview, JobRole, Organisation, User
from app.schemas.scoring import DimensionOutcome, ScoringDimension, ScoringRequest, ScoringResponse
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

    from app.services.interview_scoring import InterviewScoringError, _merge_scores

    try:
        overall, dimensions, summary, decision_fields = _merge_scores(
            model1_result, model2_result, rubric=payload.rubric
        )
    except InterviewScoringError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    # Convert dimension_outcomes to typed schema objects for the response
    raw_outcomes = decision_fields.get("dimension_outcomes") or {}
    dimension_outcomes = {
        dim: DimensionOutcome(
            outcome=data.get("outcome", "risk"),
            required_pass=data.get("required_pass", 0),
            required_watch=data.get("required_watch", 0),
            gap=data.get("gap", 0),
        )
        for dim, data in raw_outcomes.items()
        if isinstance(data, dict)
    } or None

    return ScoringResponse(
        interview_id=payload.interview_id,
        overall_score=overall,
        dimensions=dimensions,
        summary=summary,
        overall_alignment=decision_fields.get("overall_alignment"),
        overall_risk_level=decision_fields.get("overall_risk_level"),
        recommendation=decision_fields.get("recommendation"),
        dimension_outcomes=dimension_outcomes,
    )
