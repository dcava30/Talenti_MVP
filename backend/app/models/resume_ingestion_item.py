import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ResumeIngestionItem(Base):
    __tablename__ = "resume_ingestion_items"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    batch_id: Mapped[str] = mapped_column(String, ForeignKey("resume_ingestion_batches.id"))
    file_id: Mapped[str] = mapped_column(String, ForeignKey("files.id"))
    parse_status: Mapped[str] = mapped_column(String, default="pending")
    recruiter_review_status: Mapped[str] = mapped_column(String, default="pending_review")
    candidate_email: Mapped[str | None] = mapped_column(String, nullable=True)
    candidate_name: Mapped[str | None] = mapped_column(String, nullable=True)
    parse_confidence_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    parse_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    matched_user_id: Mapped[str | None] = mapped_column(String, ForeignKey("users.id"), nullable=True)
    candidate_profile_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("candidate_profiles.id"), nullable=True
    )
    application_id: Mapped[str | None] = mapped_column(String, ForeignKey("applications.id"), nullable=True)
    snapshot_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("parsed_profile_snapshots.id"), nullable=True
    )
    invitation_id: Mapped[str | None] = mapped_column(String, ForeignKey("invitations.id"), nullable=True)
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    invited_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
