import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class CandidateDei(Base):
    __tablename__ = "candidate_dei"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"))
    gender: Mapped[str | None] = mapped_column(String, nullable=True)
    ethnicity: Mapped[str | None] = mapped_column(String, nullable=True)
    disability_status: Mapped[str | None] = mapped_column(String, nullable=True)
    veteran_status: Mapped[str | None] = mapped_column(String, nullable=True)
    lgbtq_status: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
