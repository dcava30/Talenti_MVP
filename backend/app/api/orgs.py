from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import Organisation, OrgUser, User
from app.schemas.orgs import OrganisationCreate, OrganisationResponse

router = APIRouter(prefix="/api/orgs", tags=["orgs"])


@router.post("", response_model=OrganisationResponse)
def create_org(
    payload: OrganisationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OrganisationResponse:
    org = Organisation(
        name=payload.name,
        description=payload.description,
        industry=payload.industry,
        website=payload.website,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(org)
    db.flush()
    membership = OrgUser(
        organisation_id=org.id,
        user_id=user.id,
        role="admin",
        created_at=datetime.utcnow(),
    )
    db.add(membership)
    db.commit()
    db.refresh(org)
    return OrganisationResponse(
        id=org.id,
        name=org.name,
        description=org.description,
        industry=org.industry,
        website=org.website,
        created_at=org.created_at,
    )


@router.get("/{org_id}", response_model=OrganisationResponse)
def get_org(
    org_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OrganisationResponse:
    membership = (
        db.query(OrgUser)
        .filter(OrgUser.organisation_id == org_id, OrgUser.user_id == user.id)
        .first()
    )
    if not membership:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not an org member")

    org = db.query(Organisation).filter(Organisation.id == org_id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found")
    return OrganisationResponse(
        id=org.id,
        name=org.name,
        description=org.description,
        industry=org.industry,
        website=org.website,
        created_at=org.created_at,
    )
