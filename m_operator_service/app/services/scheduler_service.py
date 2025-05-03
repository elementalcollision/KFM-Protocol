from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import logging

# Assuming these imports work
from m_operator_service.app.services import maintenance_service
from m_operator_service.app.db.session import AsyncSessionLocal # Need session for db access in job
from m_operator_service.app.core.config import settings

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()

async def check_due_reviews_job():
    """Job function to check for due reviews, acquiring a DB session."""
    logger.info("Running scheduled job: check_due_reviews_job")
    async with AsyncSessionLocal() as db:
        try:
            await maintenance_service.check_for_due_reviews(db)
        except Exception as e:
            logger.exception("Error during check_due_reviews_job", exc_info=e)

async def schedule_stable_agent_reviews_job():
     """Job function to query stable agents and schedule reviews."""
     logger.info("Running scheduled job: schedule_stable_agent_reviews_job")
     async with AsyncSessionLocal() as db:
         try:
             # TODO: Implement logic to get STABLE agents (e.g., call Agent Registry)
             stable_agent_ids = [] # Placeholder
             for agent_id in stable_agent_ids:
                 # Check if a review is already scheduled or recently completed
                 # reviews = await crud.maintenance.get_reviews_by_agent(db, agent_id, status=ReviewStatus.SCHEDULED)
                 # completed = await crud.maintenance.get_reviews_by_agent(db, agent_id, status=ReviewStatus.COMPLETED)
                 # if not reviews and (not completed or completed[0].completed_date < threshold):
                 await maintenance_service.schedule_next_review(db, agent_id)
         except Exception as e:
            logger.exception("Error during schedule_stable_agent_reviews_job", exc_info=e)

def setup_scheduler():
    """Adds jobs to the scheduler."""
    # Example: Run daily at 2 AM
    scheduler.add_job(
        check_due_reviews_job,
        trigger=CronTrigger(hour=2, minute=0),
        id="check_due_reviews",
        name="Check for due/overdue maintenance reviews",
        replace_existing=True
    )
    # Example: Run weekly on Sunday at 3 AM
    scheduler.add_job(
        schedule_stable_agent_reviews_job,
        trigger=CronTrigger(day_of_week='sun', hour=3, minute=0),
        id="schedule_stable_reviews",
        name="Schedule new reviews for stable agents",
        replace_existing=True
    )
    logger.info("Maintenance scheduler jobs added.")

def start_scheduler():
    """Starts the scheduler if not already running."""
    if not scheduler.running:
        scheduler.start()
        logger.info("Maintenance scheduler started.")
    else:
        logger.info("Maintenance scheduler already running.")

def stop_scheduler():
    """Stops the scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Maintenance scheduler stopped.") 