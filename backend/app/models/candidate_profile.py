import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"))
    first_name: Mapped[str | None] = mapped_column(String, nullable=True)
    last_name: Mapped[str | None] = mapped_column(String, nullable=True)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    suburb: Mapped[str | None] = mapped_column(String, nullable=True)
    state: Mapped[str | None] = mapped_column(String, nullable=True)
    postcode: Mapped[str | None] = mapped_column(String, nullable=True)
    country: Mapped[str | None] = mapped_column(String, nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String, nullable=True)
    portfolio_url: Mapped[str | None] = mapped_column(String, nullable=True)
    cv_file_id: Mapped[str | None] = mapped_column(String, ForeignKey("files.id"), nullable=True)
    cv_file_path: Mapped[str | None] = mapped_column(String, nullable=True)
    cv_uploaded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    profile_prefilled: Mapped[bool] = mapped_column(default=False)
    profile_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    profile_review_status: Mapped[str | None] = mapped_column(String, nullable=True)
    prefill_source: Mapped[str | None] = mapped_column(String, nullable=True)
    parsed_snapshot_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("parsed_profile_snapshots.id"), nullable=True
    )
    availability: Mapped[str | None] = mapped_column(String, nullable=True)
    work_mode: Mapped[str | None] = mapped_column(String, nullable=True)
    work_rights: Mapped[str | None] = mapped_column(String, nullable=True)
    gpa_wam: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    profile_visibility: Mapped[str | None] = mapped_column(String, nullable=True)
    visibility_settings: Mapped[str | None] = mapped_column(Text, nullable=True)
    paused_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
