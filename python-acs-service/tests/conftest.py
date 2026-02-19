"""Test configuration for the ACS service."""
from __future__ import annotations

import importlib
import os
from typing import Generator

from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    """Provide a configured test client with an isolated SQLite database."""
    service_root = Path(__file__).resolve().parents[1]
    if str(service_root) not in sys.path:
        sys.path.insert(0, str(service_root))
    for module_name in list(sys.modules):
        if module_name == "app" or module_name.startswith("app."):
            del sys.modules[module_name]

    db_path = tmp_path / "test.db"
    monkeypatch.setenv("SQLITE_DB_PATH", str(db_path))
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("ENVIRONMENT", "development")

    from app import config as config_module

    importlib.reload(config_module)

    from app.db import session as session_module

    importlib.reload(session_module)

    from app.db.base import Base
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=session_module.engine)

    import app.main as main_module

    importlib.reload(main_module)

    with TestClient(main_module.app) as test_client:
        yield test_client
