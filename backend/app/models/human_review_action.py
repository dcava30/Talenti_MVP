import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class HumanReviewAction(Base):
    __tablename__ = "human_review_actions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    decision_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("decision_outcomes.id", ondelete="CASCADE"),
    )
    action_type: Mapped[str] = mapped_column(String)
    review_outcome: Mapped[str | None] = mapped_column(String, nullable=True)
    reason: Mapped[str] = mapped_column(Text)
    reviewed_by: Mapped[str] = mapped_column(String, ForeignKey("users.id"))
    notes_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    display_delta_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    decision = relationship("DecisionOutcome", back_populates="human_review_actions")
