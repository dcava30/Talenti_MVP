from __future__ import annotations

import asyncio
import logging

from app.core.config import settings
from app.core.migrations import run_startup_migrations
from app.db import get_session
from app.models import BackgroundJob
from app.services.background_jobs import claim_next_job, complete_job, fail_job, get_job_payload
from app.services.job_handlers import run_job_handler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("backend-worker")


async def _process_job(job_id: str) -> None:
    with get_session() as db:
        job = db.get(BackgroundJob, job_id)
        if not job:
            return
        try:
            result = await run_job_handler(db, job.job_type, get_job_payload(job))
            complete_job(db, job, result=result)
            db.commit()
            logger.info("Completed job %s (%s)", job.id, job.job_type)
        except Exception as exc:  # noqa: BLE001
            fail_job(db, job, str(exc))
            db.commit()
            logger.exception("Failed job %s (%s)", job.id, job.job_type)


async def main() -> None:
    poll_interval = max(0.25, settings.background_worker_poll_interval_seconds)
    run_startup_migrations()
    logger.info("Starting backend worker with poll interval %.2fs", poll_interval)
    while True:
        claimed_job_id: str | None = None
        with get_session() as db:
            job = claim_next_job(db)
            if job:
                claimed_job_id = job.id
                db.commit()
                logger.info("Claimed job %s (%s)", job.id, job.job_type)
        if claimed_job_id:
            await _process_job(claimed_job_id)
        else:
            await asyncio.sleep(poll_interval)


if __name__ == "__main__":
    asyncio.run(main())
