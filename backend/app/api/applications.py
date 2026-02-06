import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import Application, CandidateProfile, JobRole, Organisation, User
from app.schemas.applications import (
    ApplicationContextResponse,
    ApplicationCreate,
    ApplicationResponse,
    ApplicationUpdate,
    CandidateContext,
    JobContext,
    OrgContext,
)

router = APIRouter(prefix="/api/v1", tags=["applications"])


@router.post("/applications", response_model=ApplicationResponse)
def create_application(
    payload: ApplicationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ApplicationResponse:
    application = Application(
        job_role_id=payload.job_role_id,
        candidate_profile_id=payload.candidate_profile_id,
        status=payload.status or "new",
        source=payload.source,
        cover_letter=payload.cover_letter,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    return ApplicationResponse(
        id=application.id,
        job_role_id=application.job_role_id,
        candidate_profile_id=application.candidate_profile_id,
        status=application.status,
        source=application.source,
        cover_letter=application.cover_letter,
        created_at=application.created_at,
        updated_at=application.updated_at,
    )


@router.get("/applications", response_model=list[ApplicationResponse])
def list_applications(
    candidate_id: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ApplicationResponse]:
    query = db.query(Application)
    if candidate_id:
        query = query.filter(Application.candidate_profile_id == candidate_id)
    applications = query.order_by(Application.created_at.desc()).all()
    return [
        ApplicationResponse(
            id=application.id,
            job_role_id=application.job_role_id,
            candidate_profile_id=application.candidate_profile_id,
            status=application.status,
            source=application.source,
            cover_letter=application.cover_letter,
            created_at=application.created_at,
            updated_at=application.updated_at,
        )
        for application in applications
    ]


@router.patch("/applications/{application_id}", response_model=ApplicationResponse)
def update_application(
    application_id: str,
    payload: ApplicationUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ApplicationResponse:
    application = db.get(Application, application_id)
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    if payload.status is not None:
        application.status = payload.status
    if payload.source is not None:
        application.source = payload.source
    if payload.cover_letter is not None:
        application.cover_letter = payload.cover_letter
    application.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(application)
    return ApplicationResponse(
        id=application.id,
        job_role_id=application.job_role_id,
        candidate_profile_id=application.candidate_profile_id,
        status=application.status,
        source=application.source,
        cover_letter=application.cover_letter,
        created_at=application.created_at,
        updated_at=application.updated_at,
    )


@router.get("/roles/{role_id}/applications", response_model=list[ApplicationResponse])
def list_role_applications(
    role_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ApplicationResponse]:
    applications = (
        db.query(Application)
        .filter(Application.job_role_id == role_id)
        .order_by(Application.created_at.desc())
        .all()
    )
    return [
        ApplicationResponse(
            id=application.id,
            job_role_id=application.job_role_id,
            candidate_profile_id=application.candidate_profile_id,
            status=application.status,
            source=application.source,
            cover_letter=application.cover_letter,
            created_at=application.created_at,
            updated_at=application.updated_at,
        )
        for application in applications
    ]


@router.get("/applications/{application_id}/context", response_model=ApplicationContextResponse)
def get_application_context(
    application_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ApplicationContextResponse:
    application = db.get(Application, application_id)
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    job_role = db.get(JobRole, application.job_role_id)
    candidate = db.get(CandidateProfile, application.candidate_profile_id)
    organisation = db.get(Organisation, job_role.organisation_id) if job_role else None

    requirements = None
    competencies = []
    if job_role and job_role.requirements:
        try:
            requirements = json.loads(job_role.requirements)
            if isinstance(requirements, dict):
                competencies = requirements.get("skills", []) or []
            elif isinstance(requirements, list):
                competencies = requirements
        except json.JSONDecodeError:
            competencies = [line.strip() for line in job_role.requirements.splitlines() if line.strip()]
            requirements = {"raw": job_role.requirements, "skills": competencies}

    job_context = (
        JobContext(
            id=job_role.id,
            title=job_role.title,
            description=job_role.description,
            requirements=requirements,
            interview_questions=job_role.interview_structure,
        )
        if job_role
        else None
    )
    org_context = (
        OrgContext(
            id=organisation.id,
            name=organisation.name,
            values_framework=organisation.values_framework,
        )
        if organisation
        else None
    )
    candidate_context = (
        CandidateContext(
            id=candidate.id,
            first_name=candidate.first_name,
            last_name=candidate.last_name,
            email=candidate.email,
            skills=[],
            experience_years=None,
            recent_roles=[],
            education_level=None,
        )
        if candidate
        else None
    )
    return ApplicationContextResponse(
        job=job_context,
        org=org_context,
        candidate=candidate_context,
        competencies_covered=[],
        competencies_to_cover=competencies,
    )
