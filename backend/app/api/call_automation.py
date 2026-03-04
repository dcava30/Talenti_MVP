from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import Interview, User
from app.schemas.call_automation import (
    CreateCallRequest,
    CreateCallResponse,
    StartRecordingRequest,
    StartRecordingResponse,
    StopRecordingResponse,
)
from app.services.acs_worker_client import (
    AcsWorkerError,
    create_call,
    hangup_call,
    start_recording,
    stop_recording,
)
from app.core.config import settings

router = APIRouter(prefix="/api/v1/call-automation", tags=["call-automation"])


def _callback_url() -> str:
    if not settings.public_base_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PUBLIC_BASE_URL not configured",
        )
    return f"{settings.public_base_url.rstrip('/')}/api/v1/acs/webhook"


@router.post("/calls", response_model=CreateCallResponse)
async def create_interview_call(
    payload: CreateCallRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CreateCallResponse:
    interview = db.get(Interview, payload.interview_id)
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")

    try:
        result = await create_call(
            interview_id=payload.interview_id,
            target_identity=payload.target_identity,
            source_identity=payload.source_identity,
            callback_url=_callback_url(),
        )
    except AcsWorkerError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    interview.call_connection_id = result.get("call_connection_id")
    interview.server_call_id = result.get("server_call_id")
    interview.updated_at = datetime.utcnow()
    db.commit()

    return CreateCallResponse(
        call_connection_id=result.get("call_connection_id", ""),
        server_call_id=result.get("server_call_id"),
        correlation_id=result.get("correlation_id"),
    )


@router.post("/calls/{call_connection_id}/hangup")
async def hangup_interview_call(
    call_connection_id: str,
    user: User = Depends(get_current_user),
) -> dict:
    try:
        await hangup_call(call_connection_id)
    except AcsWorkerError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return {"success": True}


@router.post("/recordings/start", response_model=StartRecordingResponse)
async def start_interview_recording(
    payload: StartRecordingRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StartRecordingResponse:
    interview = db.get(Interview, payload.interview_id)
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")

    try:
        result = await start_recording(
            interview_id=payload.interview_id,
            server_call_id=payload.server_call_id,
            content_type=payload.content_type,
            channel_type=payload.channel_type,
            format_type=payload.format_type,
        )
    except AcsWorkerError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    interview.server_call_id = payload.server_call_id
    interview.recording_id = result.get("recording_id")
    interview.recording_started = True
    interview.recording_processed = False
    interview.recording_status = "recording"
    interview.recording_error = None
    interview.recording_started_at = datetime.utcnow()
    interview.updated_at = datetime.utcnow()
    db.commit()

    return StartRecordingResponse(
        recording_id=result.get("recording_id", ""),
        recording_state=result.get("recording_state", "active"),
    )


@router.post("/recordings/{recording_id}/stop", response_model=StopRecordingResponse)
async def stop_interview_recording(
    recording_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StopRecordingResponse:
    interview = db.query(Interview).filter(Interview.recording_id == recording_id).first()
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found for recording")

    try:
        result = await stop_recording(recording_id)
    except AcsWorkerError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    interview.recording_status = "processing"
    interview.recording_stopped_at = datetime.utcnow()
    interview.updated_at = datetime.utcnow()
    db.commit()

    return StopRecordingResponse(recording_state=result.get("recording_state", "stopped"))
