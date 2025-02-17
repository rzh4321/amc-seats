from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from datetime import datetime
from .check_seat import check_seats
from .db_cleanup import cleanup_database
import logging

logger = logging.getLogger(__name__)


class SeatMonitor:
    def __init__(self):
        self.scheduler = BlockingScheduler()
        self.last_execution_time = None

    def job_listener(self, event):
        if event.code == EVENT_JOB_EXECUTED:
            execution_time = (datetime.now() - self.last_execution_time).total_seconds()
            logger.info(f"Job completed in {execution_time} seconds")

            # Adjust interval based on execution time
            if execution_time > 240:  # If job takes more than 4 minutes
                current_interval = self.scheduler.get_job(
                    "check_seats"
                ).trigger.interval.seconds
                new_interval = min(
                    900, current_interval + 60
                )  # Increase interval, max 15 minutes
                self.scheduler.reschedule_job(
                    "check_seats", trigger="interval", seconds=new_interval
                )
                logger.info(f"Increased interval to {new_interval} seconds")
            elif execution_time < 180:  # If job takes less than 3 minutes
                current_interval = self.scheduler.get_job(
                    "check_seats"
                ).trigger.interval.seconds
                new_interval = max(
                    180, current_interval - 60
                )  # Decrease interval, min 3 minutes
                self.scheduler.reschedule_job(
                    "check_seats", trigger="interval", seconds=new_interval
                )
                logger.info(f"Decreased interval to {new_interval} seconds")

    def check_seats_wrapper(self):
        self.last_execution_time = datetime.now()
        check_seats()

    def run(self):
        self.scheduler.add_listener(
            self.job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR
        )
        self.scheduler.add_job(
            self.check_seats_wrapper,
            "interval",
            minutes=3,
            id="check_seats",
            max_instances=1,
            coalesce=True,  # If multiple instances are missed, only run once
        )

        self.scheduler.add_job(cleanup_database, "interval", hours=6, id="cleanup")

        logger.info("Starting scheduler...")
        # Run check_seats immediately when starting
        logger.info("Running initial check...")
        check_seats()
        # cleanup_database()
        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Scheduler stopped")


if __name__ == "__main__":
    monitor = SeatMonitor()
    monitor.run()
