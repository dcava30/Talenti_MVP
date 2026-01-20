from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_org_member
from app.models import JobRole, User
from app.schemas.shortlist import ShortlistRequest, ShortlistResponse

router = APIRouter(prefix="/api/v1/shortlist", tags=["shortlist"])


@router.post("/generate", response_model=ShortlistResponse)
def generate_shortlist(
    payload: ShortlistRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ShortlistResponse:
    job_role = db.query(JobRole).filter(JobRole.id == payload.job_role_id).first()
    if not job_role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job role not found")
    require_org_member(job_role.organisation_id, db, user)
    ranked = sorted(payload.candidates, key=lambda c: c.score, reverse=True)
    return ShortlistResponse(job_role_id=payload.job_role_id, ranked=ranked)
