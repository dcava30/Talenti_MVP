import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Education(Base):
    __tablename__ = "education"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"))
    institution: Mapped[str] = mapped_column(String)
    degree: Mapped[str] = mapped_column(String)
    field_of_study: Mapped[str | None] = mapped_column(String, nullable=True)
    start_date: Mapped[str | None] = mapped_column(String, nullable=True)
    end_date: Mapped[str | None] = mapped_column(String, nullable=True)
    grade: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
