import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ScoreDimension(Base):
    __tablename__ = "score_dimensions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    interview_id: Mapped[str] = mapped_column(String, ForeignKey("interviews.id"))

    # One of the 5 canonical dimensions: ownership | execution | challenge | ambiguity | feedback
    name: Mapped[str] = mapped_column(String)

    # Score 0-100
    score: Mapped[int] = mapped_column(Integer)

    # Evidence-derived confidence, independent of score
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Candidate-vs-environment match result
    outcome: Mapped[str | None] = mapped_column(String, nullable=True)       # pass | watch | risk
    required_pass: Mapped[int | None] = mapped_column(Integer, nullable=True)
    required_watch: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gap: Mapped[int | None] = mapped_column(Integer, nullable=True)           # score − required_pass

    # Matched keyword signal labels (JSON array)
    matched_signals: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Which model service produced this dimension score: service1 | service2 | merged
    source: Mapped[str | None] = mapped_column(String, nullable=True)

    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
