"""
Configuration settings for the ACS service.
"""
import json
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/talenti"

    # Azure Communication Services
    ACS_CONNECTION_STRING: str = ""
    ACS_ENDPOINT: str = ""
    ACS_CALLBACK_URL: str = ""

    # Internal service integration
    BACKEND_INTERNAL_URL: str = ""
    ACS_WORKER_SHARED_SECRET: str = ""

    # Azure Blob Storage
    AZURE_STORAGE_CONNECTION_STRING: str = ""
    RECORDING_CONTAINER: str = "interview-recordings"

    # Application settings
    ALLOWED_ORIGINS: List[str] = ["*"]
    FRONTEND_ORIGIN: str = ""
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "development"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        enable_decoding=False,
    )

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value: str | List[str]) -> List[str]:
        if isinstance(value, list):
            return value
        if value is None:
            return []
        raw = str(value).strip()
        if not raw:
            return []
        if raw.startswith("["):
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                inner = raw[1:-1].strip() if raw.endswith("]") else raw
                return [item.strip().strip('"').strip("'") for item in inner.split(",") if item.strip()]
            return [item for item in parsed if isinstance(item, str)]
        return [item.strip() for item in raw.split(",") if item.strip()]

settings = Settings()
