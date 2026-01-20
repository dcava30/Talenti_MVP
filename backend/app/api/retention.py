from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_org_role
from app.models import Organisation, User
from app.schemas.retention import RetentionCleanupRequest, RetentionCleanupResponse

router = APIRouter(prefix="/api/v1/data-retention", tags=["retention"])


@router.post("/cleanup", response_model=RetentionCleanupResponse)
def retention_cleanup(
    payload: RetentionCleanupRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RetentionCleanupResponse:
    organisation = db.query(Organisation).filter(Organisation.id == payload.organisation_id).first()
    if not organisation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found")
    require_org_role(payload.organisation_id, ["admin"], db, user)
    return RetentionCleanupResponse(
        interviews_removed=0,
        recordings_removed=0,
        applications_anonymized=0,
    )
