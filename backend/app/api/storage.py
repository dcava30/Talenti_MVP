from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import File, User
from app.schemas.storage import UploadUrlRequest, UploadUrlResponse
from app.services.blob_storage import build_blob_path, generate_upload_sas

router = APIRouter(prefix="/api/storage", tags=["storage"])


@router.post("/upload-url", response_model=UploadUrlResponse)
def create_upload_url(
    payload: UploadUrlRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UploadUrlResponse:
    try:
        blob_path = build_blob_path(payload.file_name)
        upload_url, expires_in = generate_upload_sas(blob_path)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    file_record = File(
        organisation_id=payload.organisation_id,
        user_id=user.id,
        blob_path=blob_path,
        content_type=payload.content_type,
        created_at=datetime.utcnow(),
    )
    db.add(file_record)
    db.commit()
    db.refresh(file_record)

    return UploadUrlResponse(
        file_id=file_record.id,
        blob_path=file_record.blob_path,
        upload_url=upload_url,
        expires_in_minutes=expires_in,
    )
