"""Azure Speech token endpoints."""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status

from app.config import settings
from app.schemas.tokens import AzureTokenResponse
from app.security.dependencies import get_current_user
from app.models.user import User
from app.services.speech_tokens import generate_speech_token

router = APIRouter()


@router.get("/token", response_model=AzureTokenResponse)
def get_speech_token(
    user: User = Depends(get_current_user),
) -> AzureTokenResponse:
    """Generate an Azure Speech token."""
    try:
        token_data = generate_speech_token()
        return AzureTokenResponse(
            token=token_data["token"],
            expires_on=datetime.fromisoformat(token_data["expires_on"]),
            mocked=False,
        )
    except RuntimeError as exc:
        if settings.ENVIRONMENT == "development":
            return AzureTokenResponse(
                token="mocked-speech-token",
                expires_on=datetime.now(timezone.utc) + timedelta(minutes=9),
                mocked=True,
                message=str(exc),
            )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
