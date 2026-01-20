from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_org_member, require_org_role
from app.models import JobRole, User
from app.schemas.roles import JobRoleCreate, JobRoleResponse

router = APIRouter(prefix="/api/roles", tags=["roles"])


@router.post("", response_model=JobRoleResponse)
def create_role(
    payload: JobRoleCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> JobRoleResponse:
    require_org_role(payload.organisation_id, ["admin", "recruiter"], db, user)
    role = JobRole(
        organisation_id=payload.organisation_id,
        title=payload.title,
        description=payload.description,
        department=payload.department,
        location=payload.location,
        work_type=payload.work_type,
        employment_type=payload.employment_type,
        status="draft",
        created_by=user.id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(role)
    db.commit()
    db.refresh(role)
    return JobRoleResponse(
        id=role.id,
        organisation_id=role.organisation_id,
        title=role.title,
        status=role.status,
        created_at=role.created_at,
    )


@router.get("/{role_id}", response_model=JobRoleResponse)
def get_role(
    role_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> JobRoleResponse:
    role = db.query(JobRole).filter(JobRole.id == role_id).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    require_org_member(role.organisation_id, db, user)
    return JobRoleResponse(
        id=role.id,
        organisation_id=role.organisation_id,
        title=role.title,
        status=role.status,
        created_at=role.created_at,
    )
