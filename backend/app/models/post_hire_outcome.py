"""
PostHireOutcome — captures post-hire performance snapshots tied to an interview score.

Supports 3-month, 6-month, and 12-month snapshots (and any custom cadence).
Links back to the InterviewScore that produced the hiring recommendation so that
outcome data can be used to validate and improve scoring accuracy over time.
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import relationship

from app.db import Base


class PostHireOutcome(Base):
    __tablename__ = "post_hire_outcomes"

    id: str = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # The interview score this outcome relates to (1:N — multiple snapshots per score)
    interview_score_id: str = Column(
        String,
        ForeignKey("interview_scores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # When was this snapshot recorded?
    observed_at: datetime = Column(DateTime, nullable=False)

    # Which snapshot cadence is this?
    # 3_month | 6_month | 12_month | custom
    snapshot_period: str = Column(String, nullable=False, default="custom")

    # Overall performance rating for this period
    # 1-5 scale: 1=poor, 2=below_expectations, 3=meets, 4=exceeds, 5=exceptional
    outcome_rating: float = Column(Float, nullable=False)

    # Free-text notes from the hiring manager or HR
    outcome_notes: str = Column(Text, nullable=True)

    # Optional: per-dimension performance ratings as JSON
    # {dimension: rating_1_to_5} — mirrors the 5 canonical scoring dimensions
    dimension_ratings: str = Column(Text, nullable=True)  # JSON

    # Who recorded this outcome (HR / hiring manager user ID)
    recorded_by: str = Column(
        String,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at: datetime = Column(DateTime, nullable=False, default=datetime.utcnow)

    # ── Relationships ─────────────────────────────────────────────────────
    interview_score = relationship("InterviewScore", back_populates="post_hire_outcomes")
    recorder = relationship("User", foreign_keys=[recorded_by])

    __table_args__ = (
        Index("ix_post_hire_outcomes_interview_score_id", "interview_score_id"),
        Index("ix_post_hire_outcomes_observed_at", "observed_at"),
        Index("ix_post_hire_outcomes_snapshot_period", "snapshot_period"),
    )
