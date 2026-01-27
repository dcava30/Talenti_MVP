"""Candidate endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.candidate import Candidate
from app.models.org_user import OrgUser
from app.models.user import User
from app.schemas.candidate import CandidateCreate, CandidateResponse
from app.security.dependencies import get_current_user

router = APIRouter()


def _get_org_id(session: Session, user: User) -> int:
    """Fetch the organisation id for the current user."""
    org_link = session.query(OrgUser).filter(OrgUser.user_id == user.id).first()
    if org_link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found")
    return org_link.organisation_id


@router.post("", response_model=CandidateResponse, status_code=status.HTTP_201_CREATED)
def create_candidate(
    payload: CandidateCreate,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CandidateResponse:
    """Create a candidate for the current organisation."""
    organisation_id = _get_org_id(session, user)
    candidate = Candidate(
        organisation_id=organisation_id,
        user_id=user.id,
        full_name=payload.full_name,
        email=payload.email,
    )
    session.add(candidate)
    session.commit()
    session.refresh(candidate)
    return candidate


@router.get("", response_model=list[CandidateResponse])
def list_candidates(
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[CandidateResponse]:
    """List candidates for the current organisation."""
    organisation_id = _get_org_id(session, user)
    return session.query(Candidate).filter(Candidate.organisation_id == organisation_id).all()


@router.get("/{candidate_id}", response_model=CandidateResponse)
def get_candidate(
    candidate_id: int,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CandidateResponse:
    """Get a candidate by id."""
    candidate = session.get(Candidate, candidate_id)
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    _get_org_id(session, user)
    return candidate
