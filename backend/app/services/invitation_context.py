from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Application, CandidateProfile, Invitation, JobRole, Organisation, User
from app.schemas.invitations import InvitationValidationResponse


def build_invitation_validation_response(
    db: Session,
    *,
    token: str,
    mark_opened: bool = False,
) -> InvitationValidationResponse:
    invitation = db.query(Invitation).filter(Invitation.token == token).first()
    if not invitation:
        return InvitationValidationResponse(valid=False)
    if invitation.expires_at < datetime.utcnow():
        return InvitationValidationResponse(valid=False)

    application = db.get(Application, invitation.application_id)
    job_role = db.get(JobRole, application.job_role_id) if application else None
    organisation = db.get(Organisation, job_role.organisation_id) if job_role else None
    profile = db.get(CandidateProfile, application.candidate_profile_id) if application else None
    candidate_user = db.get(User, profile.user_id) if profile else None

    if mark_opened and invitation.opened_at is None:
        invitation.opened_at = datetime.utcnow()

    candidate_email = (
        invitation.candidate_email
        or (profile.email if profile else None)
        or (candidate_user.email if candidate_user else None)
    )
    account_claimed = bool(candidate_user and not candidate_user.password_setup_required)
    profile_confirmed = bool(
        (profile and profile.profile_confirmed_at) or (application and application.profile_confirmed_at)
    )
    claim_required = bool(invitation.claim_required)
    profile_completion_required = bool(invitation.profile_completion_required)
    interview_unlocked = bool(
        application
        and application.status not in {"rejected", "archived"}
        and (not claim_required or account_claimed)
        and (not profile_completion_required or profile_confirmed)
    )

    return InvitationValidationResponse(
        valid=True,
        invitation={
            "id": invitation.id,
            "application_id": invitation.application_id,
            "status": invitation.status,
            "token": invitation.token,
            "candidate_email": invitation.candidate_email,
            "claim_required": invitation.claim_required,
            "profile_completion_required": invitation.profile_completion_required,
            "invitation_kind": invitation.invitation_kind,
            "expires_at": invitation.expires_at,
        },
        application={
            "id": application.id,
            "job_role_id": application.job_role_id,
            "candidate_profile_id": application.candidate_profile_id,
            "status": application.status,
            "source": application.source,
            "source_channel": application.source_channel,
            "profile_review_status": application.profile_review_status,
            "profile_confirmed_at": application.profile_confirmed_at,
        }
        if application
        else None,
        jobRole={
            "id": job_role.id,
            "title": job_role.title,
            "description": job_role.description,
            "department": job_role.department,
            "organisation": {"id": organisation.id, "name": organisation.name} if organisation else None,
        }
        if job_role
        else None,
        candidate_email=candidate_email,
        claim_required=claim_required,
        profile_completion_required=profile_completion_required,
        account_claimed=account_claimed,
        profile_confirmed=profile_confirmed,
        interview_unlocked=interview_unlocked,
    )
