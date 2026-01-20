from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_org_member
from app.models import JobRole, User
from app.schemas.roles import JobRoleCreate, JobRoleResponse

router = APIRouter(prefix="/api/roles", tags=["roles"])


@router.post("", response_model=JobRoleResponse)
def create_role(
    payload: JobRoleCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> JobRoleResponse:
    require_org_member(payload.organisation_id, db, user)
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
