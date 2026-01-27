"""
Organisation-to-user association model.
"""
from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import TimestampMixin


class OrgUser(TimestampMixin, Base):
    """Links users to organisations with optional roles."""

    __tablename__ = "org_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organisation_id: Mapped[int] = mapped_column(
        ForeignKey("organisations.id"),
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )
    role_id: Mapped[int | None] = mapped_column(
        ForeignKey("roles.id"),
        nullable=True,
    )

    organisation: Mapped["Organisation"] = relationship("Organisation", back_populates="users")
    user: Mapped["User"] = relationship("User", back_populates="organisations")
    role: Mapped["Role"] = relationship("Role", back_populates="org_users")
