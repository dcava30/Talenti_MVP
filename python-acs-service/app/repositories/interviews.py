"""
Repository for interview persistence.
"""
from typing import Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.interview import Interview


class InterviewRepository:
    """Data access helpers for interviews."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def update_recording(
        self,
        interview_id: str,
        recording_id: Optional[str] = None,
        recording_started: Optional[bool] = None,
        recording_processed: Optional[bool] = None,
        recording_url: Optional[str] = None,
    ) -> bool:
        """Update recording-related fields for an interview."""
        try:
            numeric_id = int(interview_id)
        except (TypeError, ValueError):
            return False

        try:
            interview = self._session.get(Interview, numeric_id)
            if interview is None:
                return False

            if recording_id is not None:
                interview.recording_id = recording_id
            if recording_started is not None:
                interview.recording_started = recording_started
            if recording_processed is not None:
                interview.recording_processed = recording_processed
            if recording_url is not None:
                interview.recording_url = recording_url

            self._session.commit()
            return True
        except SQLAlchemyError:
            self._session.rollback()
            return False
