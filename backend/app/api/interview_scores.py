from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import InterviewScore, User
from app.schemas.interviews import InterviewScoreResponse, InterviewScoreUpdate

router = APIRouter(prefix="/api/v1/interview-scores", tags=["interview-scores"])


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
