"""
User database model.
"""
from typing import List, Optional

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin


class User(TimestampMixin, Base):
    """Represents a user account."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    organisations: Mapped[List["OrgUser"]] = relationship(
        "OrgUser",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    candidates: Mapped[List["Candidate"]] = relationship(
        "Candidate",
        back_populates="user",
    )
