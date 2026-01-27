"""Organisation endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.organisation import Organisation
from app.models.org_user import OrgUser
from app.models.user import User
from app.schemas.organisation import OrganisationCreate, OrganisationResponse
from app.security.dependencies import get_current_user

router = APIRouter()


@router.post("", response_model=OrganisationResponse, status_code=status.HTTP_201_CREATED)
def create_organisation(
    payload: OrganisationCreate,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OrganisationResponse:
    """Create a new organisation and attach it to the current user."""
    organisation = Organisation(name=payload.name)
    session.add(organisation)
    session.flush()

    org_user = OrgUser(organisation_id=organisation.id, user_id=user.id)
    session.add(org_user)
    session.commit()
    session.refresh(organisation)
    return organisation


@router.get("/me", response_model=OrganisationResponse)
def get_my_organisation(
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OrganisationResponse:
    """Return the organisation associated with the current user."""
    org_link = session.query(OrgUser).filter(OrgUser.user_id == user.id).first()
    if org_link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found")

    organisation = session.get(Organisation, org_link.organisation_id)
    if organisation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found")

    return organisation
