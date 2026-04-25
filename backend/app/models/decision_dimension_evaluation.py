import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class DecisionDimensionEvaluation(Base):
    __tablename__ = "decision_dimension_evaluations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    decision_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("decision_outcomes.id", ondelete="CASCADE"),
    )
    dimension: Mapped[str] = mapped_column(String)
    score_internal: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence: Mapped[str | None] = mapped_column(String, nullable=True)
    required_level: Mapped[str | None] = mapped_column(String, nullable=True)
    threshold_status: Mapped[str | None] = mapped_column(String, nullable=True)
    outcome: Mapped[str | None] = mapped_column(String, nullable=True)
    evidence_summary_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    decision = relationship("DecisionOutcome", back_populates="dimension_evaluations")
