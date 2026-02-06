from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_org_member
from app.models import JobRole, User
from app.schemas.roles import JobRoleCreate, JobRoleDetail, JobRoleResponse, JobRoleRubricUpdate, JobRoleUpdate

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


@router.get("", response_model=list[JobRoleDetail])
def list_roles(
    organisation_id: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[JobRoleDetail]:
    query = db.query(JobRole)
    if organisation_id:
        require_org_member(organisation_id, db, user)
        query = query.filter(JobRole.organisation_id == organisation_id)
    roles = query.order_by(JobRole.created_at.desc()).all()
    return [
        JobRoleDetail(
            id=role.id,
            organisation_id=role.organisation_id,
            title=role.title,
            description=role.description,
            department=role.department,
            location=role.location,
            work_type=role.work_type,
            employment_type=role.employment_type,
            industry=role.industry,
            requirements=role.requirements,
            scoring_rubric=role.scoring_rubric,
            interview_structure=role.interview_structure,
            status=role.status,
            created_at=role.created_at,
            updated_at=role.updated_at,
        )
        for role in roles
    ]


@router.get("/{role_id}", response_model=JobRoleDetail)
def get_role(
    role_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> JobRoleDetail:
    role = db.get(JobRole, role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    require_org_member(role.organisation_id, db, user)
    return JobRoleDetail(
        id=role.id,
        organisation_id=role.organisation_id,
        title=role.title,
        description=role.description,
        department=role.department,
        location=role.location,
        work_type=role.work_type,
        employment_type=role.employment_type,
        industry=role.industry,
        requirements=role.requirements,
        scoring_rubric=role.scoring_rubric,
        interview_structure=role.interview_structure,
        status=role.status,
        created_at=role.created_at,
        updated_at=role.updated_at,
    )


@router.patch("/{role_id}", response_model=JobRoleDetail)
def update_role(
    role_id: str,
    payload: JobRoleUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> JobRoleDetail:
    role = db.get(JobRole, role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    require_org_member(role.organisation_id, db, user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(role, field, value)
    role.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(role)
    return JobRoleDetail(
        id=role.id,
        organisation_id=role.organisation_id,
        title=role.title,
        description=role.description,
        department=role.department,
        location=role.location,
        work_type=role.work_type,
        employment_type=role.employment_type,
        industry=role.industry,
        requirements=role.requirements,
        scoring_rubric=role.scoring_rubric,
        interview_structure=role.interview_structure,
        status=role.status,
        created_at=role.created_at,
        updated_at=role.updated_at,
    )


@router.patch("/{role_id}/rubric", response_model=JobRoleDetail)
def update_rubric(
    role_id: str,
    payload: JobRoleRubricUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> JobRoleDetail:
    role = db.get(JobRole, role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    require_org_member(role.organisation_id, db, user)
    role.scoring_rubric = payload.scoring_rubric
    role.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(role)
    return JobRoleDetail(
        id=role.id,
        organisation_id=role.organisation_id,
        title=role.title,
        description=role.description,
        department=role.department,
        location=role.location,
        work_type=role.work_type,
        employment_type=role.employment_type,
        industry=role.industry,
        requirements=role.requirements,
        scoring_rubric=role.scoring_rubric,
        interview_structure=role.interview_structure,
        status=role.status,
        created_at=role.created_at,
        updated_at=role.updated_at,
    )
