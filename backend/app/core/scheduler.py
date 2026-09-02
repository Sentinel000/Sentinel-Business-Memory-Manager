"""APScheduler daily wake-up.

The schedule does **chasing only**. Reports are generated on demand, and keeping
them apart is what makes the founder's regenerate button safe: a button that also
re-chased the whole team could not be pressed twice.
"""

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select

from app.database import SessionLocal
from app.models.company import Company
from app.services.chase_service import run_chase_cycle

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def daily_wake_up_job() -> None:
    """Run one chase cycle per tenant."""
    logger.info("Starting daily chase cycle across tenants.")

    # Ids first, in a session of its own, so the loop below does not hold a cursor
    # open across every tenant's work.
    with SessionLocal() as lookup:
        company_ids = list(lookup.execute(select(Company.id)).scalars().all())

    for company_id in company_ids:
        # A session per tenant. Sharing one across the loop means a failed
        # transaction in the first company leaves the session unusable, and every
        # tenant after it silently does nothing — which matters now that the cycle
        # writes to tasks rather than only sending messages.
        with SessionLocal() as db:
            try:
                company = db.get(Company, company_id)
                if company is None:
                    continue
                result = run_chase_cycle(db, company)
                db.commit()
                if result.reminded or result.escalated:
                    logger.info(
                        "Chased %s: %d reminded, %d handed back",
                        company.name, result.reminded, result.escalated,
                    )
            except Exception:
                db.rollback()
                logger.exception("Chase cycle failed for company %s", company_id)


def start_scheduler() -> None:
    """Initialise and start the background scheduler.

    ``BackgroundScheduler`` lives in the process, so every uvicorn worker starts its
    own and the job fires once per worker. Safe at one worker; before scaling out
    this needs a lock or an external trigger.
    """
    if not scheduler.running:
        # Daily at 08:00 UTC. The chase cadence is per-company; this is only how
        # often we check whether a cadence has elapsed.
        scheduler.add_job(
            daily_wake_up_job,
            "cron",
            hour=8,
            minute=0,
            id="sentinel_daily_chase",
            replace_existing=True,
        )
        scheduler.start()
        logger.info("APScheduler started successfully.")


def shutdown_scheduler() -> None:
    """Shutdown the background scheduler cleanly."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped.")
