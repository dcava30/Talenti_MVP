import json
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = REPO_ROOT / ".env"


class Settings(BaseSettings):
    database_url: str = "sqlite:///./data/app.db"
    jwt_secret: str
    jwt_issuer: str = "talenti"
    jwt_audience: str = "talenti-users"
    jwt_access_ttl_minutes: int = 60
    jwt_refresh_ttl_minutes: int = 60 * 24 * 30
    environment: str = "development"
    allowed_origins: list[str] = []

    azure_storage_account: str = ""
    azure_storage_account_key: str = ""
    azure_storage_container: str = ""
    azure_storage_sas_ttl_minutes: int = 15

    azure_acs_connection_string: str = ""
    azure_speech_key: str = ""
    azure_speech_region: str = ""

    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_deployment: str = ""

    # ML Model Services
    model_service_1_url: str = "http://model-service-1:8001"
    model_service_2_url: str = "http://model-service-2:8002"

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_prefix="",
        extra="ignore",
    )

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value: str | list[str]) -> list[str]:
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
                return [item.strip() for item in raw.split(",") if item.strip()]
            return [item for item in parsed if isinstance(item, str)]
        return [item.strip() for item in raw.split(",") if item.strip()]


settings = Settings()
