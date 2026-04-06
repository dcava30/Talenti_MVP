import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import InterviewScore, PostHireOutcome, User
from app.schemas.interviews import InterviewScoreResponse, InterviewScoreUpdate
from app.schemas.scoring import (
    HumanOverride,
    InterviewScoreResponse as FullInterviewScoreResponse,
    PostHireOutcomeCreate,
    PostHireOutcomeResponse,
)

router = APIRouter(prefix="/api/v1/interview-scores", tags=["interview-scores"])
logger = logging.getLogger(__name__)


@router.patch("/{score_id}", response_model=InterviewScoreResponse)
def update_score(
    score_id: str,
    payload: InterviewScoreUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> InterviewScoreResponse:
    score = db.get(InterviewScore, score_id)
    if not score:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Score not found")
    if payload.culture_fit_score is not None:
        score.culture_fit_score = payload.culture_fit_score
    if payload.summary is not None:
        score.summary = payload.summary
    if payload.recommendation is not None:
        score.recommendation = payload.recommendation
    db.commit()
    db.refresh(score)
    return InterviewScoreResponse(
        id=score.id,
        interview_id=score.interview_id,
        culture_fit_score=score.culture_fit_score,
        skills_score=score.skills_score,
        skills_outcome=score.skills_outcome,
        summary=score.summary,
        recommendation=score.recommendation,
        created_at=score.created_at,
    )


@router.post("/{score_id}/override", response_model=FullInterviewScoreResponse)
def set_human_override(
    score_id: str,
    payload: HumanOverride,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> FullInterviewScoreResponse:
    """
    B7: Record a recruiter's manual override of the automated hiring recommendation.

    Writes human_override, human_override_reason, human_override_by, and
    human_override_at to the score record. The automated recommendation field is
    left untouched — the override sits alongside it so the delta is visible.
    """
    score = db.get(InterviewScore, score_id)
    if not score:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Score not found")

    score.human_override = payload.decision
    score.human_override_reason = payload.reason
    score.human_override_by = user.id
    score.human_override_at = datetime.utcnow()

    db.commit()
    db.refresh(score)

    dim_outcomes = None
    if score.dimension_outcomes:
        try:
            dim_outcomes = json.loads(score.dimension_outcomes)
        except (json.JSONDecodeError, TypeError):
            pass

    return FullInterviewScoreResponse(
        id=score.id,
        interview_id=score.interview_id,
        culture_fit_score=score.culture_fit_score,
        skills_score=score.skills_score,
        skills_outcome=score.skills_outcome,
        overall_alignment=score.overall_alignment,
        overall_risk_level=score.overall_risk_level,
        recommendation=score.recommendation,
        human_override=score.human_override,
        human_override_reason=score.human_override_reason,
        dimension_outcomes=dim_outcomes,
        summary=score.summary,
        model_version=score.model_version,
        created_at=score.created_at,
    )


@router.post(
    "/{score_id}/outcomes",
    response_model=PostHireOutcomeResponse,
    status_code=status.HTTP_201_CREATED,
)
def record_post_hire_outcome(
    score_id: str,
    payload: PostHireOutcomeCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PostHireOutcomeResponse:
    """
    B8: Record a post-hire performance snapshot for a scored interview.

    Supports multiple snapshots per interview (3-month, 6-month, 12-month,
    or custom cadence). Outcome data is linked back to the InterviewScore for
    model validation and scoring accuracy feedback loops.
    """
    score = db.get(InterviewScore, score_id)
    if not score:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Score not found")

    dim_ratings_json: str | None = None
    if payload.dimension_ratings is not None:
        dim_ratings_json = json.dumps(payload.dimension_ratings)

    outcome = PostHireOutcome(
        interview_score_id=score_id,
        observed_at=payload.observed_at,
        snapshot_period=payload.snapshot_period,
        outcome_rating=payload.outcome_rating,
        outcome_notes=payload.outcome_notes,
        dimension_ratings=dim_ratings_json,
        recorded_by=user.id,
        created_at=datetime.utcnow(),
    )
    db.add(outcome)
    db.commit()
    db.refresh(outcome)

    dim_ratings_out: dict[str, float] | None = None
    if outcome.dimension_ratings:
        try:
            dim_ratings_out = json.loads(outcome.dimension_ratings)
        except (json.JSONDecodeError, TypeError):
            pass

    return PostHireOutcomeResponse(
        id=outcome.id,
        interview_score_id=outcome.interview_score_id,
        observed_at=outcome.observed_at,
        snapshot_period=outcome.snapshot_period,
        outcome_rating=outcome.outcome_rating,
        outcome_notes=outcome.outcome_notes,
        dimension_ratings=dim_ratings_out,
        recorded_by=outcome.recorded_by,
        created_at=outcome.created_at,
    )
