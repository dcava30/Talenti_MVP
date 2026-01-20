import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class OrgUser(Base):
    __tablename__ = "org_users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organisation_id: Mapped[str] = mapped_column(String, ForeignKey("organisations.id"))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"))
    role: Mapped[str] = mapped_column(String, default="member")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
