import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str | None] = mapped_column(String, ForeignKey("users.id"), nullable=True)
    organisation_id: Mapped[str | None] = mapped_column(String, ForeignKey("organisations.id"), nullable=True)
    action: Mapped[str] = mapped_column(String)
    entity_type: Mapped[str] = mapped_column(String)
    entity_id: Mapped[str | None] = mapped_column(String, nullable=True)
    old_values: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_values: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
