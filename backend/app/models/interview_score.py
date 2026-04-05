import uuid
from datetime import datetime
from typing import List

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class InterviewScore(Base):
    __tablename__ = "interview_scores"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    interview_id: Mapped[str] = mapped_column(String, ForeignKey("interviews.id"), unique=True)

    # Numeric aggregate
    overall_score: Mapped[int] = mapped_column(Integer)

    # Decision-dominant outputs
    overall_alignment: Mapped[str | None] = mapped_column(String, nullable=True)   # strong_fit | mixed_fit | weak_fit
    overall_risk_level: Mapped[str | None] = mapped_column(String, nullable=True)  # low | medium | high
    recommendation: Mapped[str | None] = mapped_column(String, nullable=True)      # proceed | caution | reject

    # Human override (recruiter can override the automated recommendation)
    human_override: Mapped[str | None] = mapped_column(String, nullable=True)          # proceed | caution | reject
    human_override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    human_override_by: Mapped[str | None] = mapped_column(String, nullable=True)
    human_override_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Per-dimension outcomes JSON: {dim: {outcome, required_pass, required_watch, gap}}
    dimension_outcomes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Operating environment snapshot used at scoring time (JSON)
    env_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Raw service responses (JSON) for audit / reprocessing
    service1_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    service2_raw: Mapped[str | None] = mapped_column(Text, nullable=True)

    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_version: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Back-reference to post-hire outcome snapshots (populated lazily)
    post_hire_outcomes: Mapped[List["PostHireOutcome"]] = relationship(  # noqa: F821
        "PostHireOutcome",
        back_populates="interview_score",
        cascade="all, delete-orphan",
    )
