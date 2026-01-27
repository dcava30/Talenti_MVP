"""Azure Communication Services token endpoints."""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status

from app.config import settings
from app.schemas.tokens import AzureTokenResponse
from app.security.dependencies import get_current_user
from app.models.user import User
from app.services.acs_tokens import generate_acs_token

router = APIRouter()


@router.post("/token", response_model=AzureTokenResponse)
def create_acs_token(
    user: User = Depends(get_current_user),
) -> AzureTokenResponse:
    """Generate an ACS token."""
    try:
        token_data = generate_acs_token()
        return AzureTokenResponse(
            token=token_data["token"],
            expires_on=datetime.fromisoformat(token_data["expires_on"]),
            mocked=False,
        )
    except RuntimeError as exc:
        if settings.ENVIRONMENT == "development":
            return AzureTokenResponse(
                token="mocked-acs-token",
                expires_on=datetime.now(timezone.utc) + timedelta(minutes=30),
                mocked=True,
                message=str(exc),
            )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
