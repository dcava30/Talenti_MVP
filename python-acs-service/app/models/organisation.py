"""
Organisation database model.
"""
from typing import List

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin


class Organisation(TimestampMixin, Base):
    """Represents a customer organisation."""

    __tablename__ = "organisations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    users: Mapped[List["OrgUser"]] = relationship(
        "OrgUser",
        back_populates="organisation",
        cascade="all, delete-orphan",
    )
    roles: Mapped[List["Role"]] = relationship(
        "Role",
        back_populates="organisation",
        cascade="all, delete-orphan",
    )
    candidates: Mapped[List["Candidate"]] = relationship(
        "Candidate",
        back_populates="organisation",
        cascade="all, delete-orphan",
    )
    interviews: Mapped[List["Interview"]] = relationship(
        "Interview",
        back_populates="organisation",
        cascade="all, delete-orphan",
    )
