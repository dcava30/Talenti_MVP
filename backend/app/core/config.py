from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./data/app.db"
    jwt_secret: str = "change-me"
    jwt_issuer: str = "talenti"
    jwt_audience: str = "talenti-users"
    jwt_access_ttl_minutes: int = 60
    jwt_refresh_ttl_minutes: int = 60 * 24 * 30

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

    class Config:
        env_file = ".env"
        env_prefix = ""


settings = Settings()
