"""
Configuration settings for the ACS service
"""
from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Azure Communication Services
    ACS_CONNECTION_STRING: str = ""
    ACS_ENDPOINT: str = ""
    ACS_CALLBACK_URL: str = ""  # Webhook callback URL for ACS events
    
    # Azure Blob Storage
    AZURE_STORAGE_CONNECTION_STRING: str = ""
    RECORDING_CONTAINER: str = "interview-recordings"
    
    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    
    # Azure Service Bus (for async event processing)
    SERVICE_BUS_CONNECTION_STRING: str = ""
    SERVICE_BUS_QUEUE: str = "acs-events"
    
    # Application settings
    ALLOWED_ORIGINS: List[str] = ["*"]
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "development"
    
    # Recording settings
    RECORDING_RETENTION_DAYS: int = 30
    MAX_RECORDING_DURATION_MINUTES: int = 60
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
