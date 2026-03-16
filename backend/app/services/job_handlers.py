from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.models import (
    Application,
    CandidateProfile,
    File,
    Interview,
    Invitation,
    ParsedProfileSnapshot,
    ResumeIngestionBatch,
    ResumeIngestionItem,
    User,
)
from app.services.acs_worker_client import create_call, start_recording, stop_recording
from app.services.background_jobs import enqueue_job
from app.services.domain_events import json_dumps, json_loads, record_domain_event
from app.services.interview_scoring import run_auto_scoring_for_interview
from app.services.resume_parsing import (
    apply_parsed_profile,
    create_parsed_snapshot,
    extract_resume_text,
    load_parsed_snapshot,
    parse_resume_text,
)


async def run_job_handler(db: Session, job_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    handlers = {
        "interview_start_orchestration": _handle_interview_start_orchestration,
        "interview_complete_orchestration": _handle_interview_complete_orchestration,
        "candidate_cv_postprocess": _handle_candidate_cv_postprocess,
        "bulk_resume_parse": _handle_bulk_resume_parse,
        "candidate_profile_prefill": _handle_candidate_profile_prefill,
        "candidate_invite_prepare": _handle_candidate_invite_prepare,
        "scoring_run": _handle_scoring_run,
    }
    handler = handlers.get(job_type)
    if handler is None:
        return {"status": "skipped", "reason": f"Unhandled job type: {job_type}"}
    return await handler(db, payload)


async def _handle_interview_start_orchestration(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    interview = db.get(Interview, payload.get("interview_id"))
    if not interview:
        return {"status": "skipped", "reason": "Interview not found"}

    now = datetime.utcnow()
    interview.transcript_status = interview.transcript_status or "active"
    interview.updated_at = now

    recording_consent = bool(payload.get("recording_consent"))
    call_automation = payload.get("call_automation")
    if not isinstance(call_automation, dict):
        if recording_consent and not interview.recording_status:
            interview.recording_status = "browser_managed"
        return {"status": "completed", "mode": "browser_managed"}

    target_identity = call_automation.get("target_identity")
    source_identity = call_automation.get("source_identity")
    if not target_identity or not settings.public_base_url:
        if recording_consent and not interview.recording_status:
            interview.recording_status = "browser_managed"
        return {"status": "completed", "mode": "browser_managed"}

    result = await create_call(
        interview_id=interview.id,
        target_identity=target_identity,
        source_identity=source_identity,
        callback_url=f"{settings.public_base_url.rstrip('/')}/api/v1/acs/webhook",
    )
    interview.call_connection_id = result.get("call_connection_id")
    interview.server_call_id = result.get("server_call_id")
    if recording_consent and interview.server_call_id:
        recording = await start_recording(
            interview_id=interview.id,
            server_call_id=interview.server_call_id,
            content_type="audio",
            channel_type="mixed",
            format_type="wav",
        )
        interview.recording_id = recording.get("recording_id")
        interview.recording_started = True
        interview.recording_status = "recording"
        interview.recording_started_at = now
    interview.updated_at = now
    return {"status": "completed", "mode": "server_managed"}


async def _handle_interview_complete_orchestration(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    interview = db.get(Interview, payload.get("interview_id"))
    if not interview:
        return {"status": "skipped", "reason": "Interview not found"}

    interview.transcript_status = "completed"
    interview.updated_at = datetime.utcnow()
    if interview.recording_id and interview.recording_status in {"recording", "active"}:
        await stop_recording(interview.recording_id)
        interview.recording_status = "processing"
        interview.recording_stopped_at = datetime.utcnow()
        interview.updated_at = datetime.utcnow()
        return {"status": "completed", "recording": "stop_requested"}
    return {"status": "completed", "recording": "none"}


async def _handle_candidate_cv_postprocess(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    file_record = db.get(File, payload.get("file_id"))
    profile = db.get(CandidateProfile, payload.get("candidate_profile_id"))
    user = db.get(User, profile.user_id) if profile else None
    if not file_record or not profile or not user:
        return {"status": "skipped", "reason": "Candidate CV context not found"}

    raw_text = extract_resume_text(file_record)
    parsed = parse_resume_text(raw_text, file_name=file_record.blob_path)
    snapshot = create_parsed_snapshot(
        db,
        file_id=file_record.id,
        user_id=user.id,
        parsed=parsed,
        raw_text=raw_text,
        source_kind="candidate_cv_upload",
    )
    _update_file_postprocess_metadata(
        file_record,
        status="parsed",
        snapshot_id=snapshot.id,
        extra={"source_kind": "candidate_cv_upload"},
    )
    record_domain_event(
        db=db,
        event_type="candidate.cv_parsed",
        aggregate_type="candidate_profile",
        aggregate_id=profile.id,
        payload={
            "candidate_profile_id": profile.id,
            "file_id": file_record.id,
            "snapshot_id": snapshot.id,
        },
        correlation_id=profile.id,
    )
    enqueue_job(
        db=db,
        job_type="candidate_profile_prefill",
        payload={
            "candidate_profile_id": profile.id,
            "user_id": user.id,
            "snapshot_id": snapshot.id,
            "source_kind": "candidate_cv_upload",
        },
        correlation_id=profile.id,
    )
    return {"status": "completed", "snapshot_id": snapshot.id, "next_job": "candidate_profile_prefill"}


async def _handle_bulk_resume_parse(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    item = db.get(ResumeIngestionItem, payload.get("item_id"))
    if not item:
        return {"status": "skipped", "reason": "Resume ingestion item not found"}
    batch = db.get(ResumeIngestionBatch, item.batch_id)
    file_record = db.get(File, item.file_id)
    if not batch or not file_record:
        item.parse_status = "failed"
        item.parse_error = "Batch or file record missing"
        item.updated_at = datetime.utcnow()
        return {"status": "skipped", "reason": "Batch or file record missing"}

    raw_text = extract_resume_text(file_record)
    parsed = parse_resume_text(raw_text, file_name=file_record.blob_path)
    contact = parsed.get("contact") or {}
    personal = parsed.get("personal") or {}
    email = (contact.get("email") or item.candidate_email or "").strip().lower()
    full_name = personal.get("full_name")

    item.candidate_email = email or item.candidate_email
    item.candidate_name = full_name or item.candidate_name
    item.parse_confidence_json = json_dumps(parsed.get("confidence") or {})
    item.uploaded_at = item.uploaded_at or datetime.utcnow()
    item.updated_at = datetime.utcnow()

    if not email:
        item.parse_status = "needs_email"
        item.recruiter_review_status = "needs_email"
        item.parse_error = "Could not extract a candidate email from the resume"
        _update_file_postprocess_metadata(
            file_record,
            status="needs_email",
            error=item.parse_error,
            extra={"batch_id": batch.id, "item_id": item.id},
        )
        return {"status": "completed", "result": "needs_email"}

    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            password_hash=hash_password(secrets.token_urlsafe(32)),
            full_name=full_name,
            password_setup_required=True,
            invited_via_org=True,
            source_organisation_id=batch.organisation_id,
            created_at=datetime.utcnow(),
        )
        db.add(user)
        db.flush()

    profile = db.query(CandidateProfile).filter(CandidateProfile.user_id == user.id).first()
    if not profile:
        profile = CandidateProfile(
            user_id=user.id,
            email=email,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(profile)
        db.flush()

    application = (
        db.query(Application)
        .filter(
            Application.job_role_id == batch.job_role_id,
            Application.candidate_profile_id == profile.id,
        )
        .first()
    )
    if not application:
        application = Application(
            job_role_id=batch.job_role_id,
            candidate_profile_id=profile.id,
            status="applied",
            source="external_resume_upload",
            source_batch_id=batch.id,
            source_channel="resume_batch",
            profile_review_status="needs_confirmation",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(application)
        db.flush()

    snapshot = create_parsed_snapshot(
        db,
        file_id=file_record.id,
        user_id=user.id,
        parsed=parsed,
        raw_text=raw_text,
        source_kind="org_resume_batch",
    )

    item.snapshot_id = snapshot.id
    item.matched_user_id = user.id
    item.candidate_profile_id = profile.id
    item.application_id = application.id
    item.parse_status = "parsed"
    item.parse_error = None
    item.processed_at = datetime.utcnow()
    item.updated_at = item.processed_at
    if item.recruiter_review_status == "pending_review":
        item.recruiter_review_status = "ready_for_review"

    _update_file_postprocess_metadata(
        file_record,
        status="parsed",
        snapshot_id=snapshot.id,
        extra={"batch_id": batch.id, "item_id": item.id},
    )
    record_domain_event(
        db=db,
        event_type="resume_batch.item_parsed",
        aggregate_type="resume_ingestion_item",
        aggregate_id=item.id,
        payload={
            "batch_id": batch.id,
            "item_id": item.id,
            "candidate_email": email,
            "application_id": application.id,
        },
        correlation_id=item.id,
    )
    enqueue_job(
        db=db,
        job_type="candidate_profile_prefill",
        payload={
            "candidate_profile_id": profile.id,
            "user_id": user.id,
            "application_id": application.id,
            "snapshot_id": snapshot.id,
            "item_id": item.id,
            "source_kind": "org_resume_batch",
        },
        correlation_id=item.id,
    )
    return {"status": "completed", "application_id": application.id, "snapshot_id": snapshot.id}


async def _handle_candidate_profile_prefill(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    profile = db.get(CandidateProfile, payload.get("candidate_profile_id"))
    user = db.get(User, payload.get("user_id")) if payload.get("user_id") else None
    snapshot = db.get(ParsedProfileSnapshot, payload.get("snapshot_id"))
    if not profile or not user or not snapshot:
        return {"status": "skipped", "reason": "Prefill context not found"}

    parsed = load_parsed_snapshot(snapshot)
    if not parsed:
        return {"status": "skipped", "reason": "Parsed snapshot is empty"}

    apply_parsed_profile(
        db,
        user=user,
        profile=profile,
        parsed=parsed,
        snapshot=snapshot,
        source_kind=payload.get("source_kind") or "resume",
    )
    now = datetime.utcnow()
    profile.updated_at = now

    application = db.get(Application, payload.get("application_id")) if payload.get("application_id") else None
    if application:
        application.profile_review_status = "needs_confirmation"
        application.updated_at = now

    item = db.get(ResumeIngestionItem, payload.get("item_id")) if payload.get("item_id") else None
    if item:
        item.updated_at = now

    record_domain_event(
        db=db,
        event_type="candidate.profile_prefilled",
        aggregate_type="candidate_profile",
        aggregate_id=profile.id,
        payload={
            "candidate_profile_id": profile.id,
            "application_id": application.id if application else None,
            "snapshot_id": snapshot.id,
            "source_kind": payload.get("source_kind") or "resume",
        },
        correlation_id=profile.id,
    )
    return {"status": "completed", "candidate_profile_id": profile.id, "snapshot_id": snapshot.id}


async def _handle_candidate_invite_prepare(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    item = db.get(ResumeIngestionItem, payload.get("item_id"))
    if not item:
        return {"status": "skipped", "reason": "Resume ingestion item not found"}
    if item.recruiter_review_status not in {"approved", "ready_to_invite", "ready_for_invite"}:
        return {"status": "skipped", "reason": "Item not approved for invitation"}
    if not item.application_id or not item.candidate_email:
        return {"status": "skipped", "reason": "Item missing application or candidate email"}

    invitation = db.get(Invitation, item.invitation_id) if item.invitation_id else None
    if invitation and invitation.expires_at > datetime.utcnow():
        return {"status": "completed", "invitation_id": invitation.id, "reused": True}

    now = datetime.utcnow()
    invitation = Invitation(
        application_id=item.application_id,
        token=secrets.token_urlsafe(32),
        status="pending",
        candidate_email=item.candidate_email,
        claim_required=True,
        profile_completion_required=True,
        invitation_kind="prefilled_candidate_invite",
        expires_at=now + timedelta(days=int(payload.get("expires_in_days") or 7)),
        created_at=now,
    )
    db.add(invitation)
    db.flush()

    item.invitation_id = invitation.id
    item.invited_at = now
    item.recruiter_review_status = "invited"
    item.updated_at = now

    application = db.get(Application, item.application_id)
    if application:
        application.status = "invited"
        application.updated_at = now

    record_domain_event(
        db=db,
        event_type="candidate.invitation_prepared",
        aggregate_type="resume_ingestion_item",
        aggregate_id=item.id,
        payload={
            "item_id": item.id,
            "application_id": item.application_id,
            "invitation_id": invitation.id,
            "candidate_email": item.candidate_email,
        },
        correlation_id=item.id,
    )
    return {"status": "completed", "invitation_id": invitation.id, "token": invitation.token}


async def _handle_scoring_run(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    if not settings.auto_score_interviews:
        return {"status": "skipped", "reason": "AUTO_SCORE_INTERVIEWS disabled"}
    return await run_auto_scoring_for_interview(db, payload["interview_id"])


def _update_file_postprocess_metadata(
    file_record: File,
    *,
    status: str,
    snapshot_id: str | None = None,
    error: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    metadata = json_loads(file_record.metadata_json, default={})
    if not isinstance(metadata, dict):
        metadata = {}
    metadata["postprocess"] = {
        "status": status,
        "snapshot_id": snapshot_id,
        "error": error,
        "updated_at": datetime.utcnow().isoformat(),
    }
    if extra:
        metadata["postprocess"].update(extra)
    file_record.metadata_json = json_dumps(metadata)
