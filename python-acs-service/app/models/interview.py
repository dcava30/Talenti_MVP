"""
Interview database model.
"""
from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin


class Interview(TimestampMixin, Base):
    """Represents an interview session."""

    __tablename__ = "interviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organisation_id: Mapped[int] = mapped_column(
        ForeignKey("organisations.id"),
        nullable=False,
    )
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidates.id"),
        nullable=False,
    )
    role_id: Mapped[Optional[int]] = mapped_column(ForeignKey("roles.id"))
    status: Mapped[Optional[str]] = mapped_column(String(100))
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    recording_started: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    recording_processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    recording_id: Mapped[Optional[str]] = mapped_column(String(255))
    recording_url: Mapped[Optional[str]] = mapped_column(String(1024))

    organisation: Mapped["Organisation"] = relationship("Organisation", back_populates="interviews")
    candidate: Mapped["Candidate"] = relationship("Candidate")
    role: Mapped[Optional["Role"]] = relationship("Role")
    events: Mapped[List["InterviewEvent"]] = relationship(
        "InterviewEvent",
        back_populates="interview",
        cascade="all, delete-orphan",
    )
    scores: Mapped[List["Score"]] = relationship(
        "Score",
        back_populates="interview",
        cascade="all, delete-orphan",
    )
