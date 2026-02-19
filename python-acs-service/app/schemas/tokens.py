"""Azure token response schemas."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AzureTokenResponse(BaseModel):
    """Standardized Azure token response."""

    token: str
    expires_on: datetime
    mocked: bool = False
    message: Optional[str] = Field(default=None, max_length=255)
