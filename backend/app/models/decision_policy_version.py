import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class DecisionPolicyVersion(Base):
    __tablename__ = "decision_policy_versions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organisation_id: Mapped[str] = mapped_column(String, ForeignKey("organisations.id"))
    role_id: Mapped[str | None] = mapped_column(String, ForeignKey("job_roles.id"), nullable=True)
    policy_version: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    effective_from: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    policy_definition_json: Mapped[str] = mapped_column(Text)
    critical_dimensions_json: Mapped[str] = mapped_column(Text)
    minimum_dimensions_json: Mapped[str] = mapped_column(Text)
    priority_dimensions_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
