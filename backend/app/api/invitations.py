import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import Application, CandidateProfile, Invitation, User
from app.schemas.invitations import (
    InvitationCreate,
    InvitationResponse,
    InvitationUpdate,
    InvitationValidationResponse,
)
from app.services.invitation_context import build_invitation_validation_response

router = APIRouter(prefix="/api/invitations", tags=["invitations"])
v1_router = APIRouter(prefix="/api/v1/invitations", tags=["invitations"])


def _build_response(invitation: Invitation) -> InvitationResponse:
    return InvitationResponse(
        id=invitation.id,
        application_id=invitation.application_id,
        token=invitation.token,
        status=invitation.status,
        candidate_email=invitation.candidate_email,
        claim_required=invitation.claim_required,
        profile_completion_required=invitation.profile_completion_required,
        invitation_kind=invitation.invitation_kind,
        expires_at=invitation.expires_at,
        created_at=invitation.created_at,
    )


@router.post("", response_model=InvitationResponse)
def create_invitation(
    payload: InvitationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> InvitationResponse:
    application = db.get(Application, payload.application_id)
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    profile = db.get(CandidateProfile, application.candidate_profile_id)
    candidate_user = db.get(User, profile.user_id) if profile else None

    token = secrets.token_urlsafe(32)
    invitation = Invitation(
        application_id=payload.application_id,
        token=token,
        status="pending",
        candidate_email=payload.candidate_email,
        claim_required=bool(candidate_user and candidate_user.password_setup_required),
        profile_completion_required=bool(profile and not profile.profile_confirmed_at),
        invitation_kind=(
            "prefilled_candidate_invite"
            if candidate_user and candidate_user.password_setup_required
            else "candidate_invite"
        ),
        email_template=payload.email_template,
        expires_at=payload.expires_at,
        created_at=datetime.utcnow(),
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    return _build_response(invitation)


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
    return [_build_response(invitation) for invitation in invitations]


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
    return _build_response(invitation)


@v1_router.get("/validate", response_model=InvitationValidationResponse)
def validate_invitation(
    token: str,
    db: Session = Depends(get_db),
) -> InvitationValidationResponse:
    response = build_invitation_validation_response(db, token=token, mark_opened=True)
    if response.valid:
        db.commit()
    return response
