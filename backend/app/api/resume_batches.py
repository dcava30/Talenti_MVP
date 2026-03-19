from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_org_member
from app.models import (
    File,
    JobRole,
    ResumeIngestionBatch,
    ResumeIngestionItem,
    User,
)
from app.schemas.resume_batches import (
    ResumeBatchCreate,
    ResumeBatchInviteRequest,
    ResumeBatchInviteResponse,
    ResumeBatchItemResponse,
    ResumeBatchItemUpdate,
    ResumeBatchItemUploadRequest,
    ResumeBatchItemUploadResponse,
    ResumeBatchProcessResponse,
    ResumeBatchResponse,
)
from app.services.background_jobs import enqueue_job
from app.services.blob_storage import build_blob_path, generate_upload_sas
from app.services.domain_events import json_loads, record_domain_event

router = APIRouter(prefix="/api/v1/resume-batches", tags=["resume-batches"])


def _build_batch_response(batch: ResumeIngestionBatch) -> ResumeBatchResponse:
    return ResumeBatchResponse(
        id=batch.id,
        organisation_id=batch.organisation_id,
        job_role_id=batch.job_role_id,
        status=batch.status,
        title=batch.title,
        created_by=batch.created_by,
        created_at=batch.created_at,
        updated_at=batch.updated_at,
    )


def _build_item_response(item: ResumeIngestionItem) -> ResumeBatchItemResponse:
    return ResumeBatchItemResponse(
        id=item.id,
        batch_id=item.batch_id,
        file_id=item.file_id,
        parse_status=item.parse_status,
        recruiter_review_status=item.recruiter_review_status,
        candidate_email=item.candidate_email,
        candidate_name=item.candidate_name,
        parse_confidence=json_loads(item.parse_confidence_json, default=None),
        parse_error=item.parse_error,
        matched_user_id=item.matched_user_id,
        candidate_profile_id=item.candidate_profile_id,
        application_id=item.application_id,
        snapshot_id=item.snapshot_id,
        invitation_id=item.invitation_id,
        uploaded_at=item.uploaded_at,
        processed_at=item.processed_at,
        invited_at=item.invited_at,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _get_batch_for_member(db: Session, batch_id: str, user: User) -> ResumeIngestionBatch:
    batch = db.get(ResumeIngestionBatch, batch_id)
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume batch not found")
    require_org_member(batch.organisation_id, db, user)
    return batch


@router.post("", response_model=ResumeBatchResponse)
def create_resume_batch(
    payload: ResumeBatchCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ResumeBatchResponse:
    job_role = db.get(JobRole, payload.job_role_id)
    if not job_role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job role not found")
    require_org_member(job_role.organisation_id, db, user)

    batch = ResumeIngestionBatch(
        organisation_id=job_role.organisation_id,
        job_role_id=job_role.id,
        status="draft",
        title=payload.title,
        created_by=user.id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return _build_batch_response(batch)


@router.get("/{batch_id}", response_model=ResumeBatchResponse)
def get_resume_batch(
    batch_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ResumeBatchResponse:
    batch = _get_batch_for_member(db, batch_id, user)
    return _build_batch_response(batch)


@router.get("/{batch_id}/items", response_model=list[ResumeBatchItemResponse])
def list_resume_batch_items(
    batch_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ResumeBatchItemResponse]:
    batch = _get_batch_for_member(db, batch_id, user)
    items = (
        db.query(ResumeIngestionItem)
        .filter(ResumeIngestionItem.batch_id == batch.id)
        .order_by(ResumeIngestionItem.created_at.asc())
        .all()
    )
    return [_build_item_response(item) for item in items]


@router.post("/{batch_id}/items/upload-url", response_model=ResumeBatchItemUploadResponse)
def create_resume_batch_item_upload_url(
    batch_id: str,
    payload: ResumeBatchItemUploadRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ResumeBatchItemUploadResponse:
    batch = _get_batch_for_member(db, batch_id, user)
    try:
        blob_path = build_blob_path(payload.file_name, "candidate_cv")
        upload_url, expires_in = generate_upload_sas(blob_path)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    file_record = File(
        organisation_id=batch.organisation_id,
        user_id=user.id,
        purpose="candidate_cv",
        blob_path=blob_path,
        content_type=payload.content_type,
        created_at=datetime.utcnow(),
    )
    db.add(file_record)
    db.flush()

    item = ResumeIngestionItem(
        batch_id=batch.id,
        file_id=file_record.id,
        parse_status="pending",
        recruiter_review_status="pending_review",
        uploaded_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(item)
    batch.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(item)
    return ResumeBatchItemUploadResponse(
        item_id=item.id,
        file_id=file_record.id,
        blob_path=file_record.blob_path,
        upload_url=upload_url,
        expires_in_minutes=expires_in,
    )


@router.post("/{batch_id}/process", response_model=ResumeBatchProcessResponse)
def process_resume_batch(
    batch_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ResumeBatchProcessResponse:
    batch = _get_batch_for_member(db, batch_id, user)
    items = (
        db.query(ResumeIngestionItem)
        .filter(
            ResumeIngestionItem.batch_id == batch.id,
            ResumeIngestionItem.parse_status.in_(["pending", "failed", "needs_email"]),
        )
        .all()
    )
    queued_items = 0
    for item in items:
        if not item.file_id:
            continue
        enqueue_job(
            db=db,
            job_type="bulk_resume_parse",
            payload={"item_id": item.id},
            correlation_id=item.id,
        )
        queued_items += 1

    batch.status = "processing" if queued_items else batch.status
    batch.updated_at = datetime.utcnow()
    record_domain_event(
        db=db,
        event_type="resume_batch.processing_requested",
        aggregate_type="resume_ingestion_batch",
        aggregate_id=batch.id,
        payload={"batch_id": batch.id, "queued_items": queued_items},
        correlation_id=batch.id,
    )
    db.commit()
    return ResumeBatchProcessResponse(ok=True, queued_items=queued_items)


@router.patch("/items/{item_id}", response_model=ResumeBatchItemResponse)
def update_resume_batch_item(
    item_id: str,
    payload: ResumeBatchItemUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ResumeBatchItemResponse:
    item = db.get(ResumeIngestionItem, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume batch item not found")
    batch = _get_batch_for_member(db, item.batch_id, user)

    if payload.recruiter_review_status is not None:
        item.recruiter_review_status = payload.recruiter_review_status
    if payload.candidate_email is not None:
        item.candidate_email = payload.candidate_email.strip().lower() or None
    item.updated_at = datetime.utcnow()
    batch.updated_at = item.updated_at
    db.commit()
    db.refresh(item)
    return _build_item_response(item)


@router.post("/{batch_id}/invite", response_model=ResumeBatchInviteResponse)
def invite_resume_batch_candidates(
    batch_id: str,
    payload: ResumeBatchInviteRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ResumeBatchInviteResponse:
    batch = _get_batch_for_member(db, batch_id, user)
    query = db.query(ResumeIngestionItem).filter(ResumeIngestionItem.batch_id == batch.id)
    if payload.item_ids:
        query = query.filter(ResumeIngestionItem.id.in_(payload.item_ids))
    else:
        query = query.filter(ResumeIngestionItem.recruiter_review_status.in_(["approved", "ready_to_invite"]))
    items = query.all()

    queued_items = 0
    for item in items:
        enqueue_job(
            db=db,
            job_type="candidate_invite_prepare",
            payload={"item_id": item.id, "expires_in_days": payload.expires_in_days},
            correlation_id=item.id,
        )
        queued_items += 1

    batch.status = "inviting" if queued_items else batch.status
    batch.updated_at = datetime.utcnow()
    record_domain_event(
        db=db,
        event_type="resume_batch.invite_requested",
        aggregate_type="resume_ingestion_batch",
        aggregate_id=batch.id,
        payload={"batch_id": batch.id, "queued_items": queued_items},
        correlation_id=batch.id,
    )
    db.commit()
    return ResumeBatchInviteResponse(ok=True, queued_items=queued_items)
