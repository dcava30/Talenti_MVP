from openai import AzureOpenAI

from app.core.config import settings


def get_openai_client() -> AzureOpenAI:
    return AzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version="2024-02-01",
    )
