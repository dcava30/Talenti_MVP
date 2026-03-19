from __future__ import annotations

import asyncio
import logging
import time

from app.core.config import settings
from app.core.logging import configure_logging, log_context
from app.core.migrations import run_startup_migrations
from app.db import get_session
from app.models import BackgroundJob
from app.services.background_jobs import (
    claim_next_job,
    complete_job,
    fail_job,
    get_job_payload,
    get_job_queue_metrics,
)
from app.services.job_handlers import run_job_handler

configure_logging(service_name="backend-worker", log_level=settings.log_level)
logger = logging.getLogger("backend-worker")


async def _process_job(job_id: str) -> None:
    with get_session() as db:
        job = db.get(BackgroundJob, job_id)
        if not job:
            return
        with log_context(correlation_id=job.correlation_id, job_type=job.job_type):
            try:
                result = await run_job_handler(db, job.job_type, get_job_payload(job))
                complete_job(db, job, result=result)
                db.commit()
                logger.info(
                    "Completed background job",
                    extra={"event": "job_completed", "job_id": job.id, "status": job.status},
                )
            except Exception as exc:  # noqa: BLE001
                fail_job(db, job, str(exc))
                db.commit()
                logger.exception(
                    "Failed background job",
                    extra={"event": "job_failed", "job_id": job.id, "status": job.status},
                )


async def main() -> None:
    poll_interval = max(0.25, settings.background_worker_poll_interval_seconds)
    metrics_interval = max(5.0, settings.background_worker_metrics_log_interval_seconds)
    run_startup_migrations()
    logger.info(
        "Starting backend worker",
        extra={
            "event": "worker_started",
            "poll_interval_seconds": poll_interval,
            "metrics_log_interval_seconds": metrics_interval,
        },
    )
    next_metrics_log_at = time.monotonic()
    while True:
        claimed_job_id: str | None = None
        with get_session() as db:
            if time.monotonic() >= next_metrics_log_at:
                queue_metrics = get_job_queue_metrics(db)
                logger.info("Emitting queue metrics", extra={"event": "job_queue_metrics", **queue_metrics})
                next_metrics_log_at = time.monotonic() + metrics_interval
            job = claim_next_job(db)
            if job:
                claimed_job_id = job.id
                db.commit()
                logger.info(
                    "Claimed background job",
                    extra={
                        "event": "job_claimed",
                        "job_id": job.id,
                        "job_type": job.job_type,
                        "correlation_id": job.correlation_id,
                    },
                )
        if claimed_job_id:
            await _process_job(claimed_job_id)
        else:
            await asyncio.sleep(poll_interval)


if __name__ == "__main__":
    asyncio.run(main())
