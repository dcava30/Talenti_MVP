import importlib
import sys
from datetime import datetime, timedelta

import pytest
from conftest import backend_root, clear_app_modules, prepare_test_environment, reset_database_with_migrations


def _load_modules():
    backend_path = str(backend_root())
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    prepare_test_environment()
    clear_app_modules()

    import app.services.background_jobs as background_jobs
    import app.services.blob_storage as blob_storage

    importlib.reload(background_jobs)
    importlib.reload(blob_storage)
    return background_jobs, blob_storage


def test_background_job_queue_lifecycle() -> None:
    background_jobs, _ = _load_modules()
    from app.db import SessionLocal
    from app.models import BackgroundJob

    reset_database_with_migrations()
    now = datetime.utcnow()

    with SessionLocal() as db:
        job = background_jobs.enqueue_job(
            db=db,
            job_type="scoring_run",
            payload={"interview_id": "int-123"},
            correlation_id="int-123",
            max_attempts=2,
            available_at=now - timedelta(seconds=5),
        )
        db.commit()
        db.refresh(job)

        claimed = background_jobs.claim_next_job(db)
        assert claimed is not None
        assert claimed.status == "running"
        assert claimed.attempts == 1

        payload = background_jobs.get_job_payload(claimed)
        assert payload["interview_id"] == "int-123"

        background_jobs.fail_job(db, claimed, "temporary issue", retry_delay_seconds=0)
        assert claimed.status == "pending"
        assert claimed.last_error == "temporary issue"
        db.commit()

        reclaimed = background_jobs.claim_next_job(db)
        assert reclaimed is not None
        reclaimed.attempts = reclaimed.max_attempts
        background_jobs.fail_job(db, reclaimed, "permanent issue")
        assert reclaimed.status == "failed"

        completed = background_jobs.complete_job(db, reclaimed, result={"ok": True})
        assert completed.status == "completed"
        assert "ok" in completed.result_json
        db.commit()

        invalid_payload_job = BackgroundJob(
            job_type="invalid_payload",
            status="pending",
            payload_json='["bad"]',
            available_at=datetime.utcnow(),
        )
        db.add(invalid_payload_job)
        db.commit()
        assert background_jobs.get_job_payload(invalid_payload_job) == {}

        metrics = background_jobs.get_job_queue_metrics(db)
        assert "pending_jobs" in metrics
        assert "oldest_pending_job_age_seconds" in metrics
        assert metrics["pending_jobs"] >= 0


def test_blob_storage_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    _, blob_storage = _load_modules()

    monkeypatch.setattr(blob_storage.settings, "azure_storage_account", "")
    monkeypatch.setattr(blob_storage.settings, "azure_storage_container", "")
    monkeypatch.setattr(blob_storage.settings, "azure_storage_account_key", "")
    assert blob_storage.is_blob_storage_configured() is False
    with pytest.raises(ValueError, match="required"):
        blob_storage.generate_upload_sas("candidate-cv/file.txt")
    with pytest.raises(ValueError, match="required"):
        blob_storage.download_blob_bytes("candidate-cv/file.txt")

    monkeypatch.setattr(blob_storage.settings, "azure_storage_account", "talentistorage")
    monkeypatch.setattr(blob_storage.settings, "azure_storage_container", "uploads")
    monkeypatch.setattr(blob_storage.settings, "azure_storage_account_key", "secret")
    monkeypatch.setattr(blob_storage.settings, "azure_storage_sas_ttl_minutes", 20)
    monkeypatch.setattr(blob_storage, "uuid4", lambda: "fixed-uuid")
    monkeypatch.setattr(blob_storage, "generate_blob_sas", lambda **_kwargs: "sas-token")

    class FakeDownload:
        def readall(self) -> bytes:
            return b"blob-content"

    class FakeBlobClient:
        def __init__(self, **_kwargs):
            pass

        def download_blob(self):
            return FakeDownload()

    monkeypatch.setattr(blob_storage, "BlobClient", FakeBlobClient)

    path = blob_storage.build_blob_path("Resume File.pdf", purpose="candidate_cv")
    assert path.startswith("candidate-cv/fixed-uuid-Resume-File.pdf")

    url, ttl = blob_storage.generate_upload_sas(path)
    assert "sas-token" in url
    assert ttl == 20

    raw = blob_storage.download_blob_bytes(path)
    assert raw == b"blob-content"
