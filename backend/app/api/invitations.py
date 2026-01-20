import secrets
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import Invitation, User
from app.schemas.invitations import InvitationCreate, InvitationResponse

router = APIRouter(prefix="/api/invitations", tags=["invitations"])


@router.post("", response_model=InvitationResponse)
def create_invitation(
    payload: InvitationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> InvitationResponse:
    token = secrets.token_urlsafe(32)
    invitation = Invitation(
        application_id=payload.application_id,
        token=token,
        status="pending",
        email_template=payload.email_template,
        expires_at=payload.expires_at,
        created_at=datetime.utcnow(),
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    return InvitationResponse(
        id=invitation.id,
        application_id=invitation.application_id,
        token=invitation.token,
        status=invitation.status,
        expires_at=invitation.expires_at,
        created_at=invitation.created_at,
    )
