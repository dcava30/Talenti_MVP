from datetime import datetime, timedelta
from uuid import uuid4

from azure.storage.blob import BlobSasPermissions, generate_blob_sas

from app.core.config import settings


def build_blob_path(file_name: str) -> str:
    safe_name = file_name.replace(" ", "-")
    return f"uploads/{uuid4()}-{safe_name}"


def generate_upload_sas(blob_path: str) -> tuple[str, int]:
    if (
        not settings.azure_storage_account
        or not settings.azure_storage_container
        or not settings.azure_storage_account_key
    ):
        raise ValueError("Azure storage account and container are required")

    expires_in = settings.azure_storage_sas_ttl_minutes
    expiry = datetime.utcnow() + timedelta(minutes=expires_in)

    sas_token = generate_blob_sas(
        account_name=settings.azure_storage_account,
        container_name=settings.azure_storage_container,
        blob_name=blob_path,
        account_key=settings.azure_storage_account_key or None,
        permission=BlobSasPermissions(write=True, create=True),
        expiry=expiry,
    )

    url = (
        f"https://{settings.azure_storage_account}.blob.core.windows.net/"
        f"{settings.azure_storage_container}/{blob_path}?{sas_token}"
    )
    return url, expires_in
