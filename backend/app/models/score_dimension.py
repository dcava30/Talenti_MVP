import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ScoreDimension(Base):
    __tablename__ = "score_dimensions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    interview_id: Mapped[str] = mapped_column(String, ForeignKey("interviews.id"))
    name: Mapped[str] = mapped_column(String)
    score: Mapped[int] = mapped_column(Integer)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
