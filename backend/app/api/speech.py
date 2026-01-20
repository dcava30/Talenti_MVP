from fastapi import APIRouter, Depends, HTTPException, status
import httpx
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.models import User
from app.schemas.speech import SpeechTokenResponse

router = APIRouter(prefix="/api/v1/speech", tags=["speech"])


@router.post("/token", response_model=SpeechTokenResponse)
async def speech_token(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SpeechTokenResponse:
    if not settings.azure_speech_key or not settings.azure_speech_region:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Azure Speech configuration missing",
        )

    url = f"https://{settings.azure_speech_region}.api.cognitive.microsoft.com/sts/v1.0/issueToken"
    headers = {"Ocp-Apim-Subscription-Key": settings.azure_speech_key}
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(url, headers=headers)
    if response.status_code != 200:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Speech token fetch failed")
    return SpeechTokenResponse(token=response.text, region=settings.azure_speech_region)
