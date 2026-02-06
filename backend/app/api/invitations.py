import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import Application, Invitation, JobRole, Organisation, User
from app.schemas.invitations import (
    InvitationCreate,
    InvitationResponse,
    InvitationUpdate,
    InvitationValidationResponse,
)

router = APIRouter(prefix="/api/invitations", tags=["invitations"])
v1_router = APIRouter(prefix="/api/v1/invitations", tags=["invitations"])


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


@v1_router.get("", response_model=list[InvitationResponse])
def list_invitations(
    application_id: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[InvitationResponse]:
    query = db.query(Invitation)
    if application_id:
        query = query.filter(Invitation.application_id == application_id)
    invitations = query.order_by(Invitation.created_at.desc()).all()
    return [
        InvitationResponse(
            id=invitation.id,
            application_id=invitation.application_id,
            token=invitation.token,
            status=invitation.status,
            expires_at=invitation.expires_at,
            created_at=invitation.created_at,
        )
        for invitation in invitations
    ]


@v1_router.patch("/{invitation_id}", response_model=InvitationResponse)
def update_invitation(
    invitation_id: str,
    payload: InvitationUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> InvitationResponse:
    invitation = db.get(Invitation, invitation_id)
    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")
    if payload.status is not None:
        invitation.status = payload.status
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


@v1_router.get("/validate", response_model=InvitationValidationResponse)
def validate_invitation(
    token: str,
    db: Session = Depends(get_db),
) -> InvitationValidationResponse:
    invitation = db.query(Invitation).filter(Invitation.token == token).first()
    if not invitation:
        return InvitationValidationResponse(valid=False)
    if invitation.expires_at < datetime.utcnow():
        return InvitationValidationResponse(valid=False)
    application = db.get(Application, invitation.application_id)
    job_role = db.get(JobRole, application.job_role_id) if application else None
    organisation = db.get(Organisation, job_role.organisation_id) if job_role else None
    return InvitationValidationResponse(
        valid=True,
        invitation={
            "id": invitation.id,
            "application_id": invitation.application_id,
            "status": invitation.status,
            "token": invitation.token,
            "expires_at": invitation.expires_at,
        },
        application={
            "id": application.id,
            "job_role_id": application.job_role_id,
            "candidate_profile_id": application.candidate_profile_id,
        }
        if application
        else None,
        jobRole={
            "id": job_role.id,
            "title": job_role.title,
            "organisation": {"id": organisation.id, "name": organisation.name} if organisation else None,
        }
        if job_role
        else None,
    )
