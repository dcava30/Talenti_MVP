import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Interview(Base):
    __tablename__ = "interviews"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    application_id: Mapped[str] = mapped_column(String, ForeignKey("applications.id"))
    status: Mapped[str] = mapped_column(String, default="pending")
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    call_connection_id: Mapped[str | None] = mapped_column(String, nullable=True)
    server_call_id: Mapped[str | None] = mapped_column(String, nullable=True)
    recording_id: Mapped[str | None] = mapped_column(String, nullable=True)
    recording_started: Mapped[bool] = mapped_column(Boolean, default=False)
    recording_processed: Mapped[bool] = mapped_column(Boolean, default=False)
    recording_status: Mapped[str | None] = mapped_column(String, nullable=True)
    recording_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    recording_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    recording_stopped_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    recording_processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    recording_url: Mapped[str | None] = mapped_column(String, nullable=True)
    transcript_status: Mapped[str | None] = mapped_column(String, nullable=True)
    anti_cheat_signals: Mapped[str | None] = mapped_column(Text, nullable=True)
    session_metadata: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
