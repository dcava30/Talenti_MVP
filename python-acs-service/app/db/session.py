"""
Database session management for the ACS service.
"""
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings


def _ensure_sqlite_directory(database_url: str) -> None:
    """Ensure the SQLite directory exists before connecting."""
    if not database_url.startswith("sqlite:///"):
        return
    sqlite_path = database_url.replace("sqlite:///", "", 1)
    db_file = Path(sqlite_path)
    if db_file.parent:
        db_file.parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_directory(settings.DATABASE_URL)

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    """Provide a database session for request handling."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

