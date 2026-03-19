import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_role_id: Mapped[str] = mapped_column(String, ForeignKey("job_roles.id"))
    candidate_profile_id: Mapped[str] = mapped_column(String, ForeignKey("candidate_profiles.id"))
    status: Mapped[str] = mapped_column(String, default="new")
    source: Mapped[str | None] = mapped_column(String, nullable=True)
    source_batch_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("resume_ingestion_batches.id"), nullable=True
    )
    source_channel: Mapped[str | None] = mapped_column(String, nullable=True)
    profile_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    profile_review_status: Mapped[str | None] = mapped_column(String, nullable=True)
    cover_letter: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
