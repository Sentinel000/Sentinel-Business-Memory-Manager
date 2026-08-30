"""APScheduler daily cron wake-up routine for Sentinel."""

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select

from app.agentic_ai.agents.followup import run_cron_followup
from app.database import SessionLocal
from app.models.company import Company

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def daily_wake_up_job() -> None:
    """Run daily follow-up and digest generation across all tenants."""
    logger.info("Starting daily Sentinel wake-up job across tenants.")
    db = SessionLocal()
    try:
        companies = db.execute(select(Company)).scalars().all()
        for company in companies:
            try:
                logger.info(f"Running daily follow-up for tenant {company.name} ({company.id})")
                run_cron_followup(db, company)
            except Exception as e:
                logger.error(f"Error during daily follow-up for tenant {company.id}: {e}")
    finally:
        db.close()


def start_scheduler() -> None:
    """Initialize and start the background scheduler."""
    if not scheduler.running:
        # Schedule daily at 08:00 UTC
        scheduler.add_job(
            daily_wake_up_job,
            "cron",
            hour=8,
            minute=0,
            id="sentinel_daily_followup",
            replace_existing=True,
        )
        scheduler.start()
        logger.info("APScheduler started successfully.")


def shutdown_scheduler() -> None:
    """Shutdown the background scheduler cleanly."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped.")
