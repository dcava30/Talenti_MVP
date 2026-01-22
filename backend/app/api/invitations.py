import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_org_role
from app.models import Application, JobRole
from app.models import Invitation, User
from app.schemas.invitations import InvitationCreate, InvitationResponse

router = APIRouter(prefix="/api/invitations", tags=["invitations"])


@router.post("", response_model=InvitationResponse)
def create_invitation(
    payload: InvitationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> InvitationResponse:
    application = db.query(Application).filter(Application.id == payload.application_id).first()
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    job_role = db.query(JobRole).filter(JobRole.id == application.job_role_id).first()
    if not job_role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job role not found")
    require_org_role(job_role.organisation_id, ["admin", "recruiter"], db, user)

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
