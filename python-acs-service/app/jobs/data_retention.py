"""Data retention cleanup job stub."""
from datetime import datetime, timedelta
import logging

from sqlalchemy.orm import Session

from app.config import settings
from app.models.recording import Recording

logger = logging.getLogger(__name__)


def cleanup_old_recordings(session: Session) -> int:
    """Remove recording metadata older than the retention window."""
    cutoff = datetime.utcnow() - timedelta(days=settings.RECORDING_RETENTION_DAYS)
    records = session.query(Recording).filter(Recording.created_at < cutoff).all()
    removed_count = len(records)
    for record in records:
        session.delete(record)
    if removed_count:
        session.commit()
    return removed_count
