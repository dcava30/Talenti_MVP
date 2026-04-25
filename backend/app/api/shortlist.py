from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.models import User
from app.schemas.shortlist import ShortlistRequest, ShortlistResponse

router = APIRouter(prefix="/api/v1/shortlist", tags=["shortlist"])


def _rank_candidates(payload: ShortlistRequest):
    return sorted(payload.candidates, key=lambda c: c.score, reverse=True)


@router.post("/generate", response_model=ShortlistResponse)
def generate_shortlist(
    payload: ShortlistRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ShortlistResponse:
    if settings.tds_ranking_and_shortlist_quarantine_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Shortlist generation is disabled under the TDS decisioning model.",
        )

    ranked = _rank_candidates(payload)
    return ShortlistResponse(job_role_id=payload.job_role_id, ranked=ranked)
