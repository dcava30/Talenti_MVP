from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import User
from app.schemas.scoring import ScoringDimension, ScoringRequest, ScoringResponse

router = APIRouter(prefix="/api/v1/scoring", tags=["scoring"])


@router.post("/analyze", response_model=ScoringResponse)
def score_interview(
    payload: ScoringRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ScoringResponse:
    if not payload.transcript:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Transcript required")

    rubric = payload.rubric or {"communication": 0.4, "technical": 0.6}
    total_words = sum(len(segment.content.split()) for segment in payload.transcript)
    base_score = min(100, max(40, total_words))

    dimensions = [
        ScoringDimension(
            name=name,
            score=int(base_score * weight),
            rationale=f"Score based on transcript length for {name}.",
        )
        for name, weight in rubric.items()
    ]

    overall = int(sum(d.score for d in dimensions) / max(1, len(dimensions)))
    summary = "Automated scoring based on transcript analysis."
    return ScoringResponse(
        interview_id=payload.interview_id,
        overall_score=overall,
        dimensions=dimensions,
        summary=summary,
    )
