from apscheduler.schedulers.blocking import BlockingScheduler
from datetime import datetime, timedelta
from .check_seat import check_seats
from .db_cleanup import cleanup_database
import logging
import threading
import time

logger = logging.getLogger(__name__)


class SeatMonitor:
    def __init__(self):
        self.scheduler = BlockingScheduler()
        self.lock = threading.Lock()
        self.min_interval = timedelta(minutes=3)
        self.last_run_time = None

    def check_seats_wrapper(self):
        with self.lock:
            start_time = datetime.now()
            self.last_run_time = start_time
            logger.info("Starting check_seats job...")
            check_seats()
            end_time = datetime.now()
            duration = end_time - start_time
            logger.info(f"check_seats finished in {duration.total_seconds()} seconds")

            # Calculate time to next run
            next_run_delay = max(
                5, (self.min_interval - duration).total_seconds()
            )

            if next_run_delay == 0:
                logger.info(f"Job took longer than interval. Running again immediately ({int(next_run_delay)} seconds).")
            else:
                logger.info(f"Scheduling next run in {int(next_run_delay)} seconds.")

            # Schedule the next run
            self.scheduler.add_job(
                self.check_seats_wrapper,
                "date",
                run_date=datetime.now() + timedelta(seconds=next_run_delay),
                id="check_seats",
                replace_existing=True
            )

    def run(self):
        self.scheduler.add_job(
            cleanup_database,
            "interval",
            hours=6,
            id="cleanup"
        )

        logger.info("Starting scheduler...")
        logger.info("Running initial check...")
        self.check_seats_wrapper()  # Run immediately
        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Scheduler stopped")


if __name__ == "__main__":
    monitor = SeatMonitor()
    monitor.run()