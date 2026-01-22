import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class File(Base):
    __tablename__ = "files"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organisation_id: Mapped[str | None] = mapped_column(String, ForeignKey("organisations.id"), nullable=True)
    user_id: Mapped[str | None] = mapped_column(String, ForeignKey("users.id"), nullable=True)
    blob_path: Mapped[str] = mapped_column(String, unique=True)
    content_type: Mapped[str | None] = mapped_column(String, nullable=True)
    metadata: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
