import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class DecisionRiskFlag(Base):
    __tablename__ = "decision_risk_flags"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    decision_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("decision_outcomes.id", ondelete="CASCADE"),
    )
    risk_code: Mapped[str] = mapped_column(String)
    severity: Mapped[str] = mapped_column(String)
    source_dimension: Mapped[str | None] = mapped_column(String, nullable=True)
    trigger_rule: Mapped[str | None] = mapped_column(String, nullable=True)
    context_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    decision = relationship("DecisionOutcome", back_populates="risk_flags")
