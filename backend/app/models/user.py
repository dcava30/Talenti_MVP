import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String)
    full_name: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    password_setup_required: Mapped[bool] = mapped_column(Boolean, default=False)
    account_claimed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    invited_via_org: Mapped[bool] = mapped_column(Boolean, default=False)
    source_organisation_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("organisations.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
