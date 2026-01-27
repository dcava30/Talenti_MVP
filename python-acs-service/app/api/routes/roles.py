"""Role endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.org_user import OrgUser
from app.models.role import Role
from app.models.user import User
from app.schemas.role import RoleCreate, RoleResponse, RoleUpdate
from app.security.dependencies import get_current_user

router = APIRouter()


def _resolve_org_id(session: Session, user: User, organisation_id: int | None) -> int:
    """Resolve the organisation id for the current request."""
    if organisation_id is not None:
        return organisation_id

    org_link = session.query(OrgUser).filter(OrgUser.user_id == user.id).first()
    if org_link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found")
    return org_link.organisation_id


@router.post("", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
def create_role(
    payload: RoleCreate,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RoleResponse:
    """Create a new role."""
    organisation_id = _resolve_org_id(session, user, payload.organisation_id)
    role = Role(name=payload.name, organisation_id=organisation_id)
    session.add(role)
    session.commit()
    session.refresh(role)
    return role


@router.get("", response_model=list[RoleResponse])
def list_roles(
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[RoleResponse]:
    """List roles for the current organisation."""
    organisation_id = _resolve_org_id(session, user, None)
    return session.query(Role).filter(Role.organisation_id == organisation_id).all()


@router.get("/{role_id}", response_model=RoleResponse)
def get_role(
    role_id: int,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RoleResponse:
    """Get a role by id."""
    role = session.get(Role, role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    _resolve_org_id(session, user, role.organisation_id)
    return role


@router.patch("/{role_id}", response_model=RoleResponse)
def update_role(
    role_id: int,
    payload: RoleUpdate,
    session: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RoleResponse:
    """Update a role by id."""
    role = session.get(Role, role_id)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    _resolve_org_id(session, user, role.organisation_id)

    if payload.name is not None:
        role.name = payload.name

    session.commit()
    session.refresh(role)
    return role
