import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Invitation(Base):
    __tablename__ = "invitations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    application_id: Mapped[str] = mapped_column(String, ForeignKey("applications.id"))
    token: Mapped[str] = mapped_column(String, unique=True)
    status: Mapped[str] = mapped_column(String, default="pending")
    email_template: Mapped[str | None] = mapped_column(String, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
