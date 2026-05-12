import logging
from apscheduler.schedulers.blocking import BlockingScheduler

logger = logging.getLogger(__name__)

def run_daily_cycle(is_live=False):
    logger.info("Step 1: Fetching latest daily market data...")
    logger.info("Step 2: Evaluating 10/50 SMA Trend Strategy...")
    logger.info(f"Step 3: Processing Signals... (Live Mode: {is_live})")

def start_scheduler(is_live=False):
    scheduler = BlockingScheduler(timezone='Asia/Kolkata')

    scheduler.add_job(
        run_daily_cycle,
        'cron',
        day_of_week='mon-fri',
        hour=15,
        minute=15,
        args=[is_live]
    )

    logger.info(f"Scheduler initialized. Bot is standing by for the 15:15 IST execution. (Live Mode: {is_live})")

    scheduler.start()
