"""Scoring endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.interview import Interview
from app.models.score import Score
from app.models.user import User
from app.schemas.score import ScoreCreate, ScoreResponse
from app.security.dependencies import get_current_user

router = APIRouter()


@router.post("/interview", response_model=ScoreResponse, status_code=status.HTTP_201_CREATED)
def score_interview(
    payload: ScoreCreate,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ScoreResponse:
    """Score an interview."""
    interview = session.get(Interview, payload.interview_id)
    if interview is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")

    score = Score(
        interview_id=payload.interview_id,
        score=payload.score,
        summary=payload.summary,
    )
    session.add(score)
    session.commit()
    session.refresh(score)
    return score
