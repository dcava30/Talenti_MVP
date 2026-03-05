from __future__ import annotations

import os
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config

DEFAULT_TEST_DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/talenti_test"


def backend_root() -> Path:
    return Path(__file__).resolve().parents[1]


def clear_app_modules() -> None:
    for module_name in list(sys.modules):
        if module_name == "app" or module_name.startswith("app."):
            del sys.modules[module_name]


def get_test_database_url() -> str:
    return os.environ.get("TEST_DATABASE_URL", DEFAULT_TEST_DATABASE_URL)


def prepare_test_environment() -> str:
    database_url = get_test_database_url()
    os.environ["DATABASE_URL"] = database_url
    os.environ["JWT_SECRET"] = "test-secret"
    os.environ["ALLOWED_ORIGINS"] = '["http://localhost"]'
    os.environ["ENVIRONMENT"] = "test"
    return database_url


def reset_database_with_migrations(database_url: str | None = None) -> None:
    backend_path = backend_root()
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))
    prepare_test_environment()
    if database_url is not None:
        os.environ["DATABASE_URL"] = database_url

    alembic_config = Config(str(backend_path / "alembic.ini"))
    alembic_config.set_main_option("script_location", str(backend_path / "alembic"))
    alembic_config.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])
    clear_app_modules()
    command.downgrade(alembic_config, "base")
    clear_app_modules()
    command.upgrade(alembic_config, "head")
