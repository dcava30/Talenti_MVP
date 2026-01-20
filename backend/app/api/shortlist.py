from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import User
from app.schemas.shortlist import ShortlistRequest, ShortlistResponse

router = APIRouter(prefix="/api/v1/shortlist", tags=["shortlist"])


@router.post("/generate", response_model=ShortlistResponse)
def generate_shortlist(
    payload: ShortlistRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ShortlistResponse:
    ranked = sorted(payload.candidates, key=lambda c: c.score, reverse=True)
    return ShortlistResponse(job_role_id=payload.job_role_id, ranked=ranked)
