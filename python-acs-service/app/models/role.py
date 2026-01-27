"""
Role database model.
"""
from typing import List

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin


class Role(TimestampMixin, Base):
    """Represents a role within an organisation."""

    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organisation_id: Mapped[int] = mapped_column(
        ForeignKey("organisations.id"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    organisation: Mapped["Organisation"] = relationship("Organisation", back_populates="roles")
    org_users: Mapped[List["OrgUser"]] = relationship(
        "OrgUser",
        back_populates="role",
    )
