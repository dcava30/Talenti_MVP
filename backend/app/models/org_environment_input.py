import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class OrgEnvironmentInput(Base):
    """
    Persists the raw org questionnaire answers and their translation lineage.
    One row per environment setup submission.
    Allows audit of why the operating_environment has the values it has.
    """
    __tablename__ = "org_environment_inputs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    organisation_id: Mapped[str] = mapped_column(String, ForeignKey("organisations.id", ondelete="CASCADE"))

    # Raw answers as JSON: {question_id: answer_value}
    raw_answers: Mapped[str] = mapped_column(Text)

    # Full translation lineage as JSON: list of VariableSignal dicts
    signals_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Resolved environment variables as JSON: {variable: value}
    derived_environment: Mapped[str] = mapped_column(Text)

    # Variables that fell back to defaults because no answer covered them
    defaulted_variables: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list

    # Extra fatal risk signal IDs added (e.g. from q10 coachability hard requirement)
    extra_fatal_risks: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list

    # Who submitted this setup
    submitted_by: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
