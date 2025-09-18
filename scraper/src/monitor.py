from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from .check_seat import check_seats
from .db_cleanup import cleanup_database
import logging

logger = logging.getLogger(__name__)


class SeatMonitor:
    def __init__(self):
        self.scheduler = BackgroundScheduler()

    def run(self):
        self.scheduler.add_job(cleanup_database, "interval", hours=6, id="cleanup")
        logger.info("Starting scheduler...")
        try:
            self.scheduler.start()
            check_seats()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Scheduler stopped")
        finally:
            self.scheduler.shutdown(wait=False)


if __name__ == "__main__":
    monitor = SeatMonitor()
    monitor.run()