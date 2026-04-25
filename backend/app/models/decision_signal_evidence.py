import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class DecisionSignalEvidence(Base):
    __tablename__ = "decision_signal_evidence"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    decision_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("decision_outcomes.id", ondelete="CASCADE"),
    )
    dimension: Mapped[str | None] = mapped_column(String, nullable=True)
    signal_code: Mapped[str | None] = mapped_column(String, nullable=True)
    signal_status: Mapped[str] = mapped_column(String)
    source_type: Mapped[str | None] = mapped_column(String, nullable=True)
    source_reference_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_excerpt_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    invalid_reason_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    decision = relationship("DecisionOutcome", back_populates="signal_evidence_items")
