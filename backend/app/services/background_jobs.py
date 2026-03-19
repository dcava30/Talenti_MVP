from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import BackgroundJob
from app.services.domain_events import json_dumps, json_loads


def enqueue_job(
    *,
    db: Session,
    job_type: str,
    payload: dict[str, Any],
    correlation_id: str | None = None,
    max_attempts: int = 3,
    available_at: datetime | None = None,
) -> BackgroundJob:
    job = BackgroundJob(
        job_type=job_type,
        status="pending",
        payload_json=json_dumps(payload),
        correlation_id=correlation_id,
        max_attempts=max_attempts,
        available_at=available_at or datetime.utcnow(),
    )
    db.add(job)
    return job


def claim_next_job(db: Session) -> BackgroundJob | None:
    job = db.execute(
        select(BackgroundJob)
        .where(
            BackgroundJob.status == "pending",
            BackgroundJob.available_at <= datetime.utcnow(),
        )
        .order_by(BackgroundJob.available_at.asc(), BackgroundJob.created_at.asc())
        .limit(1)
        .with_for_update(skip_locked=True)
    ).scalar_one_or_none()

    if not job:
        return None

    now = datetime.utcnow()
    job.status = "running"
    job.started_at = job.started_at or now
    job.attempts += 1
    job.last_error = None
    job.updated_at = now
    return job


def complete_job(db: Session, job: BackgroundJob, result: dict[str, Any] | None = None) -> BackgroundJob:
    job.status = "completed"
    job.result_json = json_dumps(result or {})
    job.completed_at = datetime.utcnow()
    job.updated_at = job.completed_at
    db.add(job)
    return job


def fail_job(
    db: Session,
    job: BackgroundJob,
    error_message: str,
    *,
    retry_delay_seconds: int = 30,
) -> BackgroundJob:
    job.last_error = error_message
    job.updated_at = datetime.utcnow()
    if job.attempts < job.max_attempts:
        job.status = "pending"
        job.available_at = datetime.utcnow() + timedelta(seconds=retry_delay_seconds)
    else:
        job.status = "failed"
        job.completed_at = datetime.utcnow()
    db.add(job)
    return job


def get_job_payload(job: BackgroundJob) -> dict[str, Any]:
    payload = json_loads(job.payload_json, default={})
    return payload if isinstance(payload, dict) else {}


def get_job_queue_metrics(db: Session) -> dict[str, float | int]:
    pending_count, oldest_created_at = db.execute(
        select(func.count(BackgroundJob.id), func.min(BackgroundJob.created_at)).where(
            BackgroundJob.status == "pending"
        )
    ).one()

    now = datetime.utcnow()
    oldest_pending_age_seconds = 0.0
    if oldest_created_at is not None:
        oldest_pending_age_seconds = max(0.0, (now - oldest_created_at).total_seconds())

    return {
        "pending_jobs": int(pending_count or 0),
        "oldest_pending_job_age_seconds": oldest_pending_age_seconds,
    }
