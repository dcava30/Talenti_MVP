"""Interview endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.candidate import Candidate
from app.models.interview import Interview
from app.models.interview_event import InterviewEvent
from app.models.org_user import OrgUser
from app.models.role import Role
from app.models.user import User
from app.schemas.ai import AiInterviewerRequest, AiInterviewerResponse
from app.schemas.interview import (
    InterviewCreate,
    InterviewResponse,
    InterviewEventCreate,
    InterviewEventResponse,
    InterviewCompleteResponse,
)
from app.security.dependencies import get_current_user

router = APIRouter()
ai_router = APIRouter()


def _get_org_id(session: Session, user: User) -> int:
    """Fetch the organisation id for the current user."""
    org_link = session.query(OrgUser).filter(OrgUser.user_id == user.id).first()
    if org_link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found")
    return org_link.organisation_id


@router.post("", response_model=InterviewResponse, status_code=status.HTTP_201_CREATED)
def create_interview(
    payload: InterviewCreate,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> InterviewResponse:
    """Create a new interview."""
    organisation_id = _get_org_id(session, user)

    candidate = session.get(Candidate, payload.candidate_id)
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    role_id = payload.role_id
    if role_id is not None and session.get(Role, role_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    interview = Interview(
        organisation_id=organisation_id,
        candidate_id=payload.candidate_id,
        role_id=role_id,
        status=payload.status,
        scheduled_at=payload.scheduled_at,
        notes=payload.notes,
    )
    session.add(interview)
    session.commit()
    session.refresh(interview)
    return interview


@router.get("/{interview_id}", response_model=InterviewResponse)
def get_interview(
    interview_id: int,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> InterviewResponse:
    """Fetch a single interview by id."""
    interview = session.get(Interview, interview_id)
    if interview is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
    _get_org_id(session, user)
    return interview


@router.post("/{interview_id}/events", response_model=InterviewEventResponse)
def add_interview_event(
    interview_id: int,
    payload: InterviewEventCreate,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> InterviewEventResponse:
    """Store a transcript snippet or call event."""
    interview = session.get(Interview, interview_id)
    if interview is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
    _get_org_id(session, user)

    event = InterviewEvent(
        interview_id=interview_id,
        event_type=payload.event_type,
        payload=payload.payload,
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


@router.post("/{interview_id}/complete", response_model=InterviewCompleteResponse)
def complete_interview(
    interview_id: int,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> InterviewCompleteResponse:
    """Mark an interview as completed."""
    interview = session.get(Interview, interview_id)
    if interview is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
    _get_org_id(session, user)

    interview.status = "completed"
    session.commit()
    return InterviewCompleteResponse(id=interview.id, status=interview.status or "completed")


@ai_router.post("/interviewer", response_model=AiInterviewerResponse)
def ai_interviewer(
    payload: AiInterviewerRequest,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AiInterviewerResponse:
    """Stub endpoint for AI interviewer initiation."""
    interview = session.get(Interview, payload.interview_id)
    if interview is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
    _get_org_id(session, user)

    return AiInterviewerResponse(
        status="started",
        interview_id=payload.interview_id,
        message="AI interviewer started",
    )
