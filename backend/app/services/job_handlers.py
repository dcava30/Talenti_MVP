from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import File, Interview
from app.services.acs_worker_client import create_call, start_recording, stop_recording
from app.services.domain_events import json_dumps, json_loads
from app.services.interview_scoring import run_auto_scoring_for_interview


async def run_job_handler(db: Session, job_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    handlers = {
        "interview_start_orchestration": _handle_interview_start_orchestration,
        "interview_complete_orchestration": _handle_interview_complete_orchestration,
        "candidate_cv_postprocess": _handle_candidate_cv_postprocess,
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
    if not file_record:
        return {"status": "skipped", "reason": "File not found"}

    metadata = json_loads(file_record.metadata_json, default={})
    if not isinstance(metadata, dict):
        metadata = {}
    metadata["postprocess"] = {
        "status": "pending_future_ai",
        "updated_at": datetime.utcnow().isoformat(),
    }
    file_record.metadata_json = json_dumps(metadata)
    return {"status": "completed", "postprocess": "pending_future_ai"}


async def _handle_scoring_run(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    if not settings.auto_score_interviews:
        return {"status": "skipped", "reason": "AUTO_SCORE_INTERVIEWS disabled"}
    return await run_auto_scoring_for_interview(db, payload["interview_id"])
