import logging

from celery import shared_task

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


@shared_task(name="app.worker.tasks.pkb_ingest")
def pkb_ingest_job(stats: dict) -> dict:
    """
    Example async task placeholder. Right now it simply echoes stats.

    Wire this up when heavy transforms or large files need to be offloaded.
    """
    logger.info("PKB ingest async job received", extra={"stats": stats})
    return {"status": "queued", "received": stats}
