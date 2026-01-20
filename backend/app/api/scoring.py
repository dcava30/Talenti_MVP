from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_org_member
from app.models import Application, Interview, JobRole, User
from app.schemas.scoring import ScoringDimension, ScoringRequest, ScoringResponse

router = APIRouter(prefix="/api/v1/scoring", tags=["scoring"])


@router.post("/analyze", response_model=ScoringResponse)
def score_interview(
    payload: ScoringRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ScoringResponse:
    interview = db.query(Interview).filter(Interview.id == payload.interview_id).first()
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
    application = db.query(Application).filter(Application.id == interview.application_id).first()
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    job_role = db.query(JobRole).filter(JobRole.id == application.job_role_id).first()
    if not job_role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job role not found")
    require_org_member(job_role.organisation_id, db, user)
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
