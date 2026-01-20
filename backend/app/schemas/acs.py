from datetime import datetime
from pydantic import BaseModel


class AcsTokenRequest(BaseModel):
    scopes: list[str] = ["voip"]


class AcsTokenResponse(BaseModel):
    token: str
    expires_on: datetime
    user_id: str
