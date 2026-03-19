import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ParsedProfileSnapshot(Base):
    __tablename__ = "parsed_profile_snapshots"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str | None] = mapped_column(String, ForeignKey("users.id"), nullable=True)
    file_id: Mapped[str] = mapped_column(String, ForeignKey("files.id"))
    snapshot_type: Mapped[str] = mapped_column(String, default="resume_parse")
    parser_version: Mapped[str | None] = mapped_column(String, nullable=True)
    source_kind: Mapped[str | None] = mapped_column(String, nullable=True)
    data_json: Mapped[str] = mapped_column(Text)
    confidence_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
