"""
Configuration settings for the ACS service.
"""
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    SQLITE_DB_PATH: str = "./data/app.db"

    # Azure Communication Services
    ACS_CONNECTION_STRING: str = ""
    ACS_ENDPOINT: str = ""
    ACS_CALLBACK_URL: str = ""  # Webhook callback URL for ACS events

    # Azure Cognitive Services placeholders
    AZURE_SPEECH_KEY: str = ""
    AZURE_SPEECH_REGION: str = ""
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_API_KEY: str = ""

    # Azure Blob Storage
    AZURE_STORAGE_CONNECTION_STRING: str = ""
    RECORDING_CONTAINER: str = "interview-recordings"

    # Azure Service Bus (for async event processing)
    SERVICE_BUS_CONNECTION_STRING: str = ""
    SERVICE_BUS_QUEUE: str = "acs-events"

    # Application settings
    ALLOWED_ORIGINS: List[str] = ["*"]
    FRONTEND_ORIGIN: str = ""
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "development"

    # Recording settings
    RECORDING_RETENTION_DAYS: int = 30
    MAX_RECORDING_DURATION_MINUTES: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    @property
    def DATABASE_URL(self) -> str:
        """Database URL derived from the SQLite path."""
        if self.SQLITE_DB_PATH.startswith("sqlite"):
            return self.SQLITE_DB_PATH
        return f"sqlite:///{self.SQLITE_DB_PATH}"


settings = Settings()
