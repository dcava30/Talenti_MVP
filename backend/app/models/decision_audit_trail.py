import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class DecisionAuditTrail(Base):
    __tablename__ = "decision_audit_trail"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    decision_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("decision_outcomes.id", ondelete="CASCADE"),
    )
    event_type: Mapped[str] = mapped_column(String)
    event_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    actor_type: Mapped[str] = mapped_column(String)
    actor_user_id: Mapped[str | None] = mapped_column(String, ForeignKey("users.id"), nullable=True)
    rule_version: Mapped[str | None] = mapped_column(String, nullable=True)
    policy_version: Mapped[str | None] = mapped_column(String, nullable=True)
    event_payload_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    decision = relationship("DecisionOutcome", back_populates="audit_trail_entries")
