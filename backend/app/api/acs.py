from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.models import Interview, User
from app.schemas.call_automation import WorkerRecordingEvent
from app.schemas.acs import AcsTokenRequest, AcsTokenResponse
from app.services.acs_service import get_acs_client

router = APIRouter(prefix="/api/v1/acs", tags=["acs"])


@router.post("/token", response_model=AcsTokenResponse)
def create_acs_token(
    payload: AcsTokenRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AcsTokenResponse:
    if not settings.azure_acs_connection_string:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AZURE_ACS_CONNECTION_STRING not configured",
        )
    client = get_acs_client()
    identity = client.create_user()
    token = client.get_token(identity, payload.scopes)
    user_id = getattr(identity, "communication_user_id", None) or identity.properties.get("id")
    return AcsTokenResponse(token=token.token, expires_on=token.expires_on, user_id=user_id)


@router.post("/webhook")
async def acs_webhook(request: Request, db: Session = Depends(get_db)) -> dict:
    payload = await request.json()
    if isinstance(payload, list) and payload:
        event = payload[0]
        if event.get("eventType") == "Microsoft.EventGrid.SubscriptionValidationEvent":
            return {"validationResponse": event.get("data", {}).get("validationCode")}

        data = event.get("data", {})
        recording_id = data.get("recordingId")
        call_connection_id = data.get("callConnectionId")
        if recording_id:
            interview = db.query(Interview).filter(Interview.recording_id == recording_id).first()
            if interview:
                interview.recording_status = event.get("eventType", "acs_event")
                interview.updated_at = datetime.utcnow()
                db.commit()
        elif call_connection_id:
            interview = (
                db.query(Interview).filter(Interview.call_connection_id == call_connection_id).first()
            )
            if interview:
                interview.updated_at = datetime.utcnow()
                db.commit()
    return {"ok": True}


@router.post("/worker-events")
def acs_worker_events(
    payload: WorkerRecordingEvent,
    db: Session = Depends(get_db),
    x_acs_worker_secret: str | None = Header(default=None),
) -> dict:
    if not settings.acs_worker_shared_secret:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="ACS worker secret missing")
    if x_acs_worker_secret != settings.acs_worker_shared_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid worker secret")

    interview = db.get(Interview, payload.interview_id)
    if not interview and payload.recording_id:
        interview = db.query(Interview).filter(Interview.recording_id == payload.recording_id).first()
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")

    interview.recording_id = payload.recording_id
    interview.recording_status = payload.status
    interview.recording_processed = payload.status == "completed"
    interview.recording_error = payload.error_message
    if payload.recording_url:
        interview.recording_url = payload.recording_url
    interview.recording_processed_at = payload.processed_at or datetime.utcnow()
    interview.updated_at = datetime.utcnow()
    db.commit()
    return {"ok": True}
