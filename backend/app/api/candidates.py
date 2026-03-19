from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import (
    Application,
    CandidateProfile,
    CandidateSkill,
    DataDeletionRequest,
    Education,
    EmploymentHistory,
    File as StoredFile,
    Invitation,
    JobRole,
    Organisation,
    PracticeInterview,
    User,
)
from app.schemas.candidates import (
    CandidateApplicationResponse,
    CandidateProfileCreate,
    CandidateProfileResponse,
    DeletionRequestCreate,
    DeletionRequestResponse,
    EducationCreate,
    EducationResponse,
    EducationUpdate,
    CandidateProfileConfirmRequest,
    CandidateProfileConfirmResponse,
    EmploymentCreate,
    EmploymentResponse,
    EmploymentUpdate,
    ParseResumeRequest,
    ParseResumeResponse,
    ParsedResume,
    PracticeInterviewCreate,
    PracticeInterviewResponse,
    PracticeInterviewUpdate,
    SkillCreate,
    SkillResponse,
)
from app.services.background_jobs import enqueue_job
from app.services.blob_storage import is_blob_storage_configured
from app.services.domain_events import record_domain_event
from app.services.resume_parsing import extract_resume_text, parse_resume_text

router = APIRouter(prefix="/api/v1/candidates", tags=["candidates"])


def _build_profile_response(profile: CandidateProfile):
    return CandidateProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        first_name=profile.first_name,
        last_name=profile.last_name,
        email=profile.email,
        phone=profile.phone,
        suburb=profile.suburb,
        state=profile.state,
        postcode=profile.postcode,
        country=profile.country,
        linkedin_url=profile.linkedin_url,
        portfolio_url=profile.portfolio_url,
        cv_file_id=profile.cv_file_id,
        cv_file_path=profile.cv_file_path,
        profile_prefilled=profile.profile_prefilled,
        profile_confirmed_at=profile.profile_confirmed_at,
        profile_review_status=profile.profile_review_status,
        prefill_source=profile.prefill_source,
        parsed_snapshot_id=profile.parsed_snapshot_id,
        availability=profile.availability,
        work_mode=profile.work_mode,
        work_rights=profile.work_rights,
        gpa_wam=float(profile.gpa_wam) if profile.gpa_wam is not None else None,
        profile_visibility=profile.profile_visibility,
        visibility_settings=profile.visibility_settings,
        paused_at=profile.paused_at,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def _build_candidate_application_response(
    app: Application,
    role: JobRole | None,
    organisation: Organisation | None,
) -> CandidateApplicationResponse:
    return CandidateApplicationResponse(
        id=app.id,
        job_role_id=app.job_role_id,
        candidate_profile_id=app.candidate_profile_id,
        status=app.status,
        source=app.source,
        source_channel=app.source_channel,
        profile_confirmed_at=app.profile_confirmed_at,
        profile_review_status=app.profile_review_status,
        created_at=app.created_at,
        updated_at=app.updated_at,
        job_roles=(
            {
                "id": role.id,
                "title": role.title,
                "organisations": {"id": organisation.id, "name": organisation.name}
                if organisation
                else None,
            }
            if role
            else None
        ),
    )


def _queue_candidate_cv_postprocess(
    db: Session,
    *,
    profile: CandidateProfile,
    file_record: StoredFile,
    storage_mode: str,
) -> None:
    profile.cv_file_id = file_record.id
    profile.cv_file_path = file_record.blob_path
    profile.cv_uploaded_at = datetime.utcnow()
    profile.profile_review_status = "pending_parse"
    profile.profile_confirmed_at = None
    record_domain_event(
        db=db,
        event_type="candidate.cv_uploaded",
        aggregate_type="candidate_profile",
        aggregate_id=profile.id,
        payload={
            "candidate_profile_id": profile.id,
            "file_id": file_record.id,
            "storage_mode": storage_mode,
        },
        correlation_id=profile.id,
    )
    enqueue_job(
        db=db,
        job_type="candidate_cv_postprocess",
        payload={"candidate_profile_id": profile.id, "file_id": file_record.id},
        correlation_id=profile.id,
    )


def _resolve_cv_file(
    db: Session,
    *,
    cv_file_id: str | None,
    target_user_id: str,
) -> StoredFile | None:
    if not cv_file_id:
        return None
    file_record = db.get(StoredFile, cv_file_id)
    if not file_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Uploaded CV file not found")
    if file_record.user_id not in {None, target_user_id}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Uploaded CV file not accessible")
    return file_record


@router.post("/parse-resume", response_model=ParseResumeResponse)
def parse_resume(
    payload: ParseResumeRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ParseResumeResponse:
    resume_text = payload.resume_text
    if payload.file_id:
        file_record = _resolve_cv_file(db, cv_file_id=payload.file_id, target_user_id=user.id)
        if not file_record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Uploaded CV file not found")
        resume_text = extract_resume_text(file_record)
    if not resume_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide file_id or resume_text to parse a resume.",
        )

    parsed_payload = parse_resume_text(resume_text)
    parsed = ParsedResume(
        full_name=(parsed_payload.get("personal") or {}).get("full_name"),
        email=(parsed_payload.get("contact") or {}).get("email"),
        phone=(parsed_payload.get("contact") or {}).get("phone"),
        skills=parsed_payload.get("skills") or [],
        linkedin_url=(parsed_payload.get("contact") or {}).get("linkedin_url"),
        portfolio_url=(parsed_payload.get("contact") or {}).get("portfolio_url"),
        summary=parsed_payload.get("summary"),
        employment=parsed_payload.get("employment") or [],
        education=parsed_payload.get("education") or [],
        confidence=parsed_payload.get("confidence") or {},
    )
    return ParseResumeResponse(candidate_id=payload.candidate_id or user.id, parsed=parsed)


@router.get("/profile", response_model=CandidateProfileResponse | None)
def get_profile(
    user_id: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CandidateProfileResponse | None:
    target_user_id = user_id or user.id
    profile = db.query(CandidateProfile).filter(CandidateProfile.user_id == target_user_id).first()
    if not profile:
        return None
    return _build_profile_response(profile)


@router.post("/profile", response_model=CandidateProfileResponse)
def upsert_profile(
    payload: CandidateProfileCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CandidateProfileResponse:
    target_user_id = payload.user_id or user.id
    profile = db.query(CandidateProfile).filter(CandidateProfile.user_id == target_user_id).first()
    if not profile:
        profile = CandidateProfile(
            user_id=target_user_id,
            created_at=datetime.utcnow(),
        )
        db.add(profile)
        db.flush()
    linked_cv_file = _resolve_cv_file(db, cv_file_id=payload.cv_file_id, target_user_id=target_user_id)
    for field, value in payload.model_dump(
        exclude_unset=True,
        exclude={
            "user_id",
            "profile_prefilled",
            "profile_confirmed_at",
            "profile_review_status",
            "prefill_source",
            "parsed_snapshot_id",
        },
    ).items():
        setattr(profile, field, value)
    if linked_cv_file:
        _queue_candidate_cv_postprocess(
            db,
            profile=profile,
            file_record=linked_cv_file,
            storage_mode="blob",
        )
    profile.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(profile)
    return _build_profile_response(profile)


@router.patch("/{user_id}/profile", response_model=CandidateProfileResponse)
def update_profile(
    user_id: str,
    payload: CandidateProfileCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CandidateProfileResponse:
    if user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    profile = db.query(CandidateProfile).filter(CandidateProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    linked_cv_file = _resolve_cv_file(db, cv_file_id=payload.cv_file_id, target_user_id=user_id)
    for field, value in payload.model_dump(
        exclude_unset=True,
        exclude={
            "user_id",
            "profile_prefilled",
            "profile_confirmed_at",
            "profile_review_status",
            "prefill_source",
            "parsed_snapshot_id",
        },
    ).items():
        setattr(profile, field, value)
    if linked_cv_file:
        _queue_candidate_cv_postprocess(
            db,
            profile=profile,
            file_record=linked_cv_file,
            storage_mode="blob",
        )
    profile.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(profile)
    return _build_profile_response(profile)


@router.post("/profile/confirm", response_model=CandidateProfileConfirmResponse)
def confirm_profile(
    payload: CandidateProfileConfirmRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CandidateProfileConfirmResponse:
    profile = db.query(CandidateProfile).filter(CandidateProfile.user_id == user.id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")

    application = None
    if payload.application_id:
        application = db.get(Application, payload.application_id)
    elif payload.invitation_token:
        invitation = db.query(Invitation).filter(Invitation.token == payload.invitation_token).first()
        application = db.get(Application, invitation.application_id) if invitation else None

    if application and application.candidate_profile_id != profile.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Application not accessible")

    now = datetime.utcnow()
    profile.profile_confirmed_at = now
    profile.profile_review_status = "confirmed"
    profile.updated_at = now
    if application:
        application.profile_confirmed_at = now
        application.profile_review_status = "confirmed"
        application.updated_at = now

    record_domain_event(
        db=db,
        event_type="candidate.profile_confirmed",
        aggregate_type="candidate_profile",
        aggregate_id=profile.id,
        payload={
            "candidate_profile_id": profile.id,
            "application_id": application.id if application else None,
            "user_id": user.id,
        },
        correlation_id=profile.id,
    )
    db.commit()
    return CandidateProfileConfirmResponse(ok=True, profile_confirmed_at=now, interview_unlocked=True)


@router.get("/employment", response_model=list[EmploymentResponse])
def list_employment(
    user_id: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[EmploymentResponse]:
    target_user_id = user_id or user.id
    entries = (
        db.query(EmploymentHistory)
        .filter(EmploymentHistory.user_id == target_user_id)
        .order_by(EmploymentHistory.created_at.desc())
        .all()
    )
    return [
        EmploymentResponse(
            id=entry.id,
            user_id=entry.user_id,
            company=entry.company,
            title=entry.title,
            location=entry.location,
            start_date=entry.start_date,
            end_date=entry.end_date,
            description=entry.description,
            created_at=entry.created_at,
        )
        for entry in entries
    ]


@router.post("/employment", response_model=EmploymentResponse)
def create_employment(
    payload: EmploymentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> EmploymentResponse:
    if payload.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    entry = EmploymentHistory(
        user_id=payload.user_id,
        company=payload.company,
        title=payload.title,
        location=payload.location,
        start_date=payload.start_date,
        end_date=payload.end_date,
        description=payload.description,
        created_at=datetime.utcnow(),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return EmploymentResponse(
        id=entry.id,
        user_id=entry.user_id,
        company=entry.company,
        title=entry.title,
        location=entry.location,
        start_date=entry.start_date,
        end_date=entry.end_date,
        description=entry.description,
        created_at=entry.created_at,
    )


@router.patch("/employment/{employment_id}", response_model=EmploymentResponse)
def update_employment(
    employment_id: str,
    payload: EmploymentUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> EmploymentResponse:
    entry = db.get(EmploymentHistory, employment_id)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employment not found")
    if entry.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(entry, field, value)
    db.commit()
    db.refresh(entry)
    return EmploymentResponse(
        id=entry.id,
        user_id=entry.user_id,
        company=entry.company,
        title=entry.title,
        location=entry.location,
        start_date=entry.start_date,
        end_date=entry.end_date,
        description=entry.description,
        created_at=entry.created_at,
    )


@router.delete("/employment/{employment_id}")
def delete_employment(
    employment_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    entry = db.get(EmploymentHistory, employment_id)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employment not found")
    if entry.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    db.delete(entry)
    db.commit()
    return {"ok": True}


@router.get("/education", response_model=list[EducationResponse])
def list_education(
    user_id: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[EducationResponse]:
    target_user_id = user_id or user.id
    entries = (
        db.query(Education)
        .filter(Education.user_id == target_user_id)
        .order_by(Education.created_at.desc())
        .all()
    )
    return [
        EducationResponse(
            id=entry.id,
            user_id=entry.user_id,
            institution=entry.institution,
            degree=entry.degree,
            field_of_study=entry.field_of_study,
            start_date=entry.start_date,
            end_date=entry.end_date,
            grade=entry.grade,
            created_at=entry.created_at,
        )
        for entry in entries
    ]


@router.post("/education", response_model=EducationResponse)
def create_education(
    payload: EducationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> EducationResponse:
    if payload.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    entry = Education(
        user_id=payload.user_id,
        institution=payload.institution,
        degree=payload.degree,
        field_of_study=payload.field_of_study,
        start_date=payload.start_date,
        end_date=payload.end_date,
        grade=payload.grade,
        created_at=datetime.utcnow(),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return EducationResponse(
        id=entry.id,
        user_id=entry.user_id,
        institution=entry.institution,
        degree=entry.degree,
        field_of_study=entry.field_of_study,
        start_date=entry.start_date,
        end_date=entry.end_date,
        grade=entry.grade,
        created_at=entry.created_at,
    )


@router.patch("/education/{education_id}", response_model=EducationResponse)
def update_education(
    education_id: str,
    payload: EducationUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> EducationResponse:
    entry = db.get(Education, education_id)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Education not found")
    if entry.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(entry, field, value)
    db.commit()
    db.refresh(entry)
    return EducationResponse(
        id=entry.id,
        user_id=entry.user_id,
        institution=entry.institution,
        degree=entry.degree,
        field_of_study=entry.field_of_study,
        start_date=entry.start_date,
        end_date=entry.end_date,
        grade=entry.grade,
        created_at=entry.created_at,
    )


@router.delete("/education/{education_id}")
def delete_education(
    education_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    entry = db.get(Education, education_id)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Education not found")
    if entry.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    db.delete(entry)
    db.commit()
    return {"ok": True}


@router.get("/skills", response_model=list[SkillResponse])
def list_skills(
    user_id: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[SkillResponse]:
    target_user_id = user_id or user.id
    entries = (
        db.query(CandidateSkill)
        .filter(CandidateSkill.user_id == target_user_id)
        .order_by(CandidateSkill.created_at.desc())
        .all()
    )
    return [
        SkillResponse(
            id=entry.id,
            user_id=entry.user_id,
            skill_name=entry.skill_name,
            skill_type=entry.skill_type,
            proficiency_level=entry.proficiency_level,
            created_at=entry.created_at,
        )
        for entry in entries
    ]


@router.post("/skills", response_model=SkillResponse)
def create_skill(
    payload: SkillCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SkillResponse:
    if payload.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    entry = CandidateSkill(
        user_id=payload.user_id,
        skill_name=payload.skill_name,
        skill_type=payload.skill_type,
        proficiency_level=payload.proficiency_level,
        created_at=datetime.utcnow(),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return SkillResponse(
        id=entry.id,
        user_id=entry.user_id,
        skill_name=entry.skill_name,
        skill_type=entry.skill_type,
        proficiency_level=entry.proficiency_level,
        created_at=entry.created_at,
    )


@router.delete("/skills/{skill_id}")
def delete_skill(
    skill_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    entry = db.get(CandidateSkill, skill_id)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
    if entry.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    db.delete(entry)
    db.commit()
    return {"ok": True}


@router.get("/applications", response_model=list[CandidateApplicationResponse])
def list_candidate_applications(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[CandidateApplicationResponse]:
    profile = db.query(CandidateProfile).filter(CandidateProfile.user_id == user.id).first()
    if not profile:
        return []
    applications = (
        db.query(Application)
        .filter(Application.candidate_profile_id == profile.id)
        .order_by(Application.created_at.desc())
        .all()
    )
    role_ids = [app.job_role_id for app in applications]
    roles = {role.id: role for role in db.query(JobRole).filter(JobRole.id.in_(role_ids)).all()}
    organisations = {}
    if role_ids:
        org_ids = {role.organisation_id for role in roles.values()}
        organisations = {
            org.id: org
            for org in db.query(Organisation).filter(Organisation.id.in_(org_ids)).all()
        }
    response = []
    for app in applications:
        role = roles.get(app.job_role_id)
        organisation = organisations.get(role.organisation_id) if role else None
        response.append(_build_candidate_application_response(app, role, organisation))
    return response


@router.post("/applications", response_model=dict)
def create_candidate_application(
    payload: dict,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    job_role_id = payload.get("job_role_id")
    candidate_id = payload.get("candidate_id") or user.id
    if not job_role_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="job_role_id required")
    candidate_user = db.get(User, candidate_id)
    profile = db.query(CandidateProfile).filter(CandidateProfile.user_id == candidate_id).first()
    if not profile:
        profile = CandidateProfile(
            user_id=candidate_id,
            email=candidate_user.email if candidate_user else user.email,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(profile)
        db.flush()
    application = Application(
        job_role_id=job_role_id,
        candidate_profile_id=profile.id,
        status=payload.get("status") or "applied",
        source=payload.get("source"),
        source_batch_id=payload.get("source_batch_id"),
        source_channel=payload.get("source_channel"),
        profile_review_status=payload.get("profile_review_status"),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    return {"id": application.id}


@router.get("/invitations", response_model=list[dict])
def list_candidate_invitations(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[dict]:
    profile = db.query(CandidateProfile).filter(CandidateProfile.user_id == user.id).first()
    if not profile:
        return []
    invitations = (
        db.query(Invitation)
        .join(Application, Invitation.application_id == Application.id)
        .filter(Application.candidate_profile_id == profile.id)
        .order_by(Invitation.created_at.desc())
        .all()
    )
    return [
        {
            "id": invitation.id,
            "application_id": invitation.application_id,
            "token": invitation.token,
            "status": invitation.status,
            "candidate_email": invitation.candidate_email,
            "claim_required": invitation.claim_required,
            "profile_completion_required": invitation.profile_completion_required,
            "invitation_kind": invitation.invitation_kind,
            "expires_at": invitation.expires_at,
            "created_at": invitation.created_at,
        }
        for invitation in invitations
    ]


@router.get("/feedback", response_model=list[dict])
def list_candidate_feedback(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[dict]:
    return []


@router.get("/practice-interviews", response_model=list[PracticeInterviewResponse])
def list_practice_interviews(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[PracticeInterviewResponse]:
    interviews = (
        db.query(PracticeInterview)
        .filter(PracticeInterview.user_id == user.id)
        .order_by(PracticeInterview.created_at.desc())
        .all()
    )
    return [
        PracticeInterviewResponse(
            id=interview.id,
            user_id=interview.user_id,
            sample_role_type=interview.sample_role_type,
            status=interview.status,
            started_at=interview.started_at,
            ended_at=interview.ended_at,
            duration_seconds=interview.duration_seconds,
            feedback=interview.feedback,
            created_at=interview.created_at,
        )
        for interview in interviews
    ]


@router.post("/practice-interviews", response_model=PracticeInterviewResponse)
def create_practice_interview(
    payload: PracticeInterviewCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PracticeInterviewResponse:
    interview = PracticeInterview(
        user_id=user.id,
        sample_role_type=payload.sample_role_type,
        status=payload.status or "pending",
        created_at=datetime.utcnow(),
    )
    db.add(interview)
    db.commit()
    db.refresh(interview)
    return PracticeInterviewResponse(
        id=interview.id,
        user_id=interview.user_id,
        sample_role_type=interview.sample_role_type,
        status=interview.status,
        started_at=interview.started_at,
        ended_at=interview.ended_at,
        duration_seconds=interview.duration_seconds,
        feedback=interview.feedback,
        created_at=interview.created_at,
    )


@router.patch("/practice-interviews/{practice_id}", response_model=PracticeInterviewResponse)
def update_practice_interview(
    practice_id: str,
    payload: PracticeInterviewUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PracticeInterviewResponse:
    interview = db.get(PracticeInterview, practice_id)
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Practice interview not found")
    if interview.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(interview, field, value)
    db.commit()
    db.refresh(interview)
    return PracticeInterviewResponse(
        id=interview.id,
        user_id=interview.user_id,
        sample_role_type=interview.sample_role_type,
        status=interview.status,
        started_at=interview.started_at,
        ended_at=interview.ended_at,
        duration_seconds=interview.duration_seconds,
        feedback=interview.feedback,
        created_at=interview.created_at,
    )


@router.get("/practice-interviews/{practice_id}", response_model=PracticeInterviewResponse)
def get_practice_interview(
    practice_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PracticeInterviewResponse:
    interview = db.get(PracticeInterview, practice_id)
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Practice interview not found")
    if interview.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return PracticeInterviewResponse(
        id=interview.id,
        user_id=interview.user_id,
        sample_role_type=interview.sample_role_type,
        status=interview.status,
        started_at=interview.started_at,
        ended_at=interview.ended_at,
        duration_seconds=interview.duration_seconds,
        feedback=interview.feedback,
        created_at=interview.created_at,
    )


@router.get("/deletion-requests", response_model=list[DeletionRequestResponse])
def list_deletion_requests(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[DeletionRequestResponse]:
    requests = (
        db.query(DataDeletionRequest)
        .filter(DataDeletionRequest.user_id == user.id)
        .order_by(DataDeletionRequest.requested_at.desc())
        .all()
    )
    return [
        DeletionRequestResponse(
            id=req.id,
            user_id=req.user_id,
            request_type=req.request_type,
            status=req.status,
            reason=req.reason,
            notes=req.notes,
            requested_at=req.requested_at,
            processed_at=req.processed_at,
            processed_by=req.processed_by,
        )
        for req in requests
    ]


@router.post("/deletion-requests", response_model=DeletionRequestResponse)
def create_deletion_request(
    payload: DeletionRequestCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DeletionRequestResponse:
    request = DataDeletionRequest(
        user_id=user.id,
        request_type=payload.request_type,
        status="pending",
        reason=payload.reason,
        requested_at=datetime.utcnow(),
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return DeletionRequestResponse(
        id=request.id,
        user_id=request.user_id,
        request_type=request.request_type,
        status=request.status,
        reason=request.reason,
        notes=request.notes,
        requested_at=request.requested_at,
        processed_at=request.processed_at,
        processed_by=request.processed_by,
    )


@router.delete("/{user_id}")
def delete_account(
    user_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    if user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    profile = db.query(CandidateProfile).filter(CandidateProfile.user_id == user_id).first()
    if profile:
        db.delete(profile)
    db.delete(user)
    db.commit()
    return {"ok": True}


@router.post("/cv", response_model=dict)
def upload_cv(
    candidate_id: str | None = None,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    if is_blob_storage_configured():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Direct CV upload is disabled when Blob Storage is configured. Use /api/storage/upload-url.",
        )
    target_user_id = candidate_id or user.id
    upload_dir = Path("data/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / f"{datetime.utcnow().timestamp()}-{file.filename}"
    with file_path.open("wb") as buffer:
        buffer.write(file.file.read())
    stored_file = StoredFile(
        user_id=target_user_id,
        purpose="candidate_cv",
        blob_path=str(file_path),
        content_type=file.content_type,
        created_at=datetime.utcnow(),
    )
    db.add(stored_file)
    db.flush()
    profile = db.query(CandidateProfile).filter(CandidateProfile.user_id == target_user_id).first()
    if not profile:
        target_user = db.get(User, target_user_id)
        profile = CandidateProfile(
            user_id=target_user_id,
            email=target_user.email if target_user else user.email,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(profile)
        db.flush()
    _queue_candidate_cv_postprocess(
        db,
        profile=profile,
        file_record=stored_file,
        storage_mode="local_fallback",
    )
    profile.updated_at = datetime.utcnow()
    db.commit()
    return {
        "cv_file_id": stored_file.id,
        "cv_file_path": profile.cv_file_path,
    }
