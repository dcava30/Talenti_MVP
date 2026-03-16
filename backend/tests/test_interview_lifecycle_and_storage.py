import importlib
import io
import sys
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from conftest import backend_root, clear_app_modules, prepare_test_environment, reset_database_with_migrations


def create_client() -> TestClient:
    pytest.importorskip("email_validator")
    backend_path = str(backend_root())
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    database_url = prepare_test_environment()
    reset_database_with_migrations(database_url)
    clear_app_modules()
    import app.core.config as config

    importlib.reload(config)
    import app.main as main

    importlib.reload(main)
    return TestClient(main.app)


def _create_user_and_token(db):
    from app.core.security import create_access_token, hash_password
    from app.models import User

    user = User(
        email="storage-tester@example.com",
        password_hash=hash_password("password"),
        full_name="Storage Tester",
        created_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user, create_access_token(user.id)


def _create_application_graph(db, user_id: str) -> str:
    from app.models import Application, CandidateProfile, JobRole, Organisation

    organisation = Organisation(name="Talenti Org", values_framework='{"operating_environment": {"control_vs_autonomy": "full_ownership"}, "taxonomy": {"taxonomy_id": "tax", "version": "1.0", "signals": []}}')
    db.add(organisation)
    db.flush()

    role = JobRole(
        organisation_id=organisation.id,
        title="Backend Engineer",
        description="Build APIs",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(role)
    db.flush()

    profile = CandidateProfile(
        user_id=user_id,
        email="storage-tester@example.com",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(profile)
    db.flush()

    application = Application(
        job_role_id=role.id,
        candidate_profile_id=profile.id,
        status="invited",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    return application.id


def test_storage_upload_url_can_link_candidate_cv(monkeypatch: pytest.MonkeyPatch) -> None:
    client = create_client()
    client.get("/health")

    from app.api import storage as storage_api
    from app.db import SessionLocal
    from app.models import BackgroundJob, DomainEvent

    monkeypatch.setattr(storage_api, "generate_upload_sas", lambda blob_path: (f"https://example.com/{blob_path}", 15))

    with SessionLocal() as db:
        user, token = _create_user_and_token(db)

    upload_response = client.post(
        "/api/storage/upload-url",
        json={"file_name": "resume.pdf", "content_type": "application/pdf", "purpose": "candidate_cv"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert upload_response.status_code == 200
    payload = upload_response.json()
    assert payload["blob_path"].startswith("candidate-cv/")

    profile_response = client.post(
        "/api/v1/candidates/profile",
        json={"user_id": user.id, "cv_file_id": payload["file_id"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert profile_response.status_code == 200
    assert profile_response.json()["cv_file_id"] == payload["file_id"]
    assert profile_response.json()["cv_file_path"] == payload["blob_path"]

    with SessionLocal() as db:
        assert db.query(DomainEvent).filter(DomainEvent.event_type == "candidate.cv_uploaded").count() == 1
        assert db.query(BackgroundJob).filter(BackgroundJob.job_type == "candidate_cv_postprocess").count() == 1


def test_direct_cv_upload_rejected_when_blob_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    client = create_client()
    client.get("/health")

    from app.api import candidates as candidates_api
    from app.db import SessionLocal

    monkeypatch.setattr(candidates_api, "is_blob_storage_configured", lambda: True)

    with SessionLocal() as db:
        user, token = _create_user_and_token(db)

    response = client.post(
        "/api/v1/candidates/cv",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("resume.txt", io.BytesIO(b"resume"), "text/plain")},
        data={"candidate_id": user.id},
    )
    assert response.status_code == 400
    assert "Blob Storage" in response.json()["detail"]


def test_interview_start_and_complete_emit_events_and_jobs() -> None:
    client = create_client()
    client.get("/health")

    from app.db import SessionLocal
    from app.models import Application, BackgroundJob, DomainEvent

    with SessionLocal() as db:
        user, token = _create_user_and_token(db)
        application_id = _create_application_graph(db, user.id)

    start_response = client.post(
        "/api/v1/interviews/start",
        json={
            "application_id": application_id,
            "recording_consent": True,
            "client_capabilities": {"media_devices": True},
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert start_response.status_code == 200
    interview_id = start_response.json()["id"]
    assert start_response.json()["status"] == "in_progress"

    complete_response = client.post(
        f"/api/v1/interviews/{interview_id}/complete",
        json={"duration_seconds": 123, "anti_cheat_signals": [{"type": "tab_switch"}]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert complete_response.status_code == 200
    assert complete_response.json()["status"] == "completed"

    with SessionLocal() as db:
        application = db.get(Application, application_id)
        assert application is not None
        assert application.status == "scoring"

        event_types = {
            event.event_type
            for event in db.query(DomainEvent).filter(DomainEvent.aggregate_id == interview_id).all()
        }
        assert {"interview.started", "interview.completed", "scoring.requested"} <= event_types

        job_types = {
            job.job_type
            for job in db.query(BackgroundJob).filter(BackgroundJob.correlation_id == interview_id).all()
        }
        assert {
            "interview_start_orchestration",
            "interview_complete_orchestration",
            "scoring_run",
        } <= job_types
