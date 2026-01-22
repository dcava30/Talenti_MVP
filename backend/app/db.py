from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import settings


def _enable_sqlite_foreign_keys(dbapi_connection, connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)

if settings.database_url.startswith("sqlite"):
    event.listen(engine, "connect", _enable_sqlite_foreign_keys)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

Base = declarative_base()


@contextmanager
def get_session() -> Session:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
