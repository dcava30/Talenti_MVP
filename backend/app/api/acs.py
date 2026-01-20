from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.models import User
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
async def acs_webhook(request: Request) -> dict:
    payload = await request.json()
    if isinstance(payload, list) and payload:
        event = payload[0]
        if event.get("eventType") == "Microsoft.EventGrid.SubscriptionValidationEvent":
            return {"validationResponse": event.get("data", {}).get("validationCode")}
    return {"ok": True}
