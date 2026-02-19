"""
Candidate database model.
"""
from typing import Optional

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin


class Candidate(TimestampMixin, Base):
    """Represents a candidate profile."""

    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organisation_id: Mapped[int] = mapped_column(
        ForeignKey("organisations.id"),
        nullable=False,
    )
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    email: Mapped[Optional[str]] = mapped_column(String(255))

    organisation: Mapped["Organisation"] = relationship("Organisation", back_populates="candidates")
    user: Mapped[Optional["User"]] = relationship("User", back_populates="candidates")
