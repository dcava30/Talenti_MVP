from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import User
from app.schemas.retention import RetentionCleanupRequest, RetentionCleanupResponse

router = APIRouter(prefix="/api/v1/data-retention", tags=["retention"])


@router.post("/cleanup", response_model=RetentionCleanupResponse)
def retention_cleanup(
    payload: RetentionCleanupRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RetentionCleanupResponse:
    return RetentionCleanupResponse(
        interviews_removed=0,
        recordings_removed=0,
        applications_anonymized=0,
    )
