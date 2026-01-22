from pydantic import BaseModel


class SpeechTokenResponse(BaseModel):
    token: str
    region: str
