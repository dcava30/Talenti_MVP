from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from app.core.config import settings

STARTUP_MIGRATION_LOCK_KEY = 841937264102


def _build_alembic_config() -> Config:
    backend_root = Path(__file__).resolve().parents[2]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", settings.database_url)
    return config


def run_startup_migrations() -> None:
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    with engine.connect() as connection:
        if connection.dialect.name != "postgresql":
            raise RuntimeError("DATABASE_URL must point to a PostgreSQL database.")
        connection.execute(
            text("SELECT pg_advisory_lock(:lock_key)"),
            {"lock_key": STARTUP_MIGRATION_LOCK_KEY},
        )
        try:
            config = _build_alembic_config()
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
        finally:
            connection.execute(
                text("SELECT pg_advisory_unlock(:lock_key)"),
                {"lock_key": STARTUP_MIGRATION_LOCK_KEY},
            )
