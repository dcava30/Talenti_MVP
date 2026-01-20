from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_org_member
from app.models import JobRole, User
from app.schemas.requirements import ExtractRequirementsRequest, ExtractRequirementsResponse

router = APIRouter(prefix="/api/v1/roles", tags=["roles-ai"])


@router.post("/extract-requirements", response_model=ExtractRequirementsResponse)
def extract_requirements(
    payload: ExtractRequirementsRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ExtractRequirementsResponse:
    job_role = db.query(JobRole).filter(JobRole.id == payload.job_role_id).first()
    if not job_role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job role not found")
    require_org_member(job_role.organisation_id, db, user)

    if not payload.job_description:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Job description required")

    sentences = [s.strip() for s in payload.job_description.split(".") if s.strip()]
    skills = [s for s in sentences if "experience" in s.lower()]
    responsibilities = sentences[:3]
    qualifications = sentences[3:6]

    return ExtractRequirementsResponse(
        skills=skills,
        responsibilities=responsibilities,
        qualifications=qualifications,
    )
