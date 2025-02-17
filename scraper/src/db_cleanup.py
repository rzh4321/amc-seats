from datetime import datetime, timedelta, timezone
import logging
from .db import SessionLocal, SeatNotification, Movie, Theater, Showtime
from sqlalchemy import or_, and_, delete
import pytz


logger = logging.getLogger(__name__)


def cleanup_database():
    logger.info("Starting database cleanup...")
    with SessionLocal() as session:
        try:
            # Delete old movies (not detected in last 30 days)
            thirty_days_ago = datetime.now() - timedelta(days=30)
            old_movies = (
                session.query(Movie).filter(Movie.last_detected < thirty_days_ago).all()
            )
            logger.info(f"found {len(old_movies)} old movies...")

            for movie in old_movies:
                logger.info(f"Deleting old movie: {movie.name}")
                session.delete(
                    movie
                )  # Will cascade delete related showtimes and notifications

            now = datetime.now(timezone.utc)
            # Delete past showtimes
            past_showtimes = (
                session.query(Showtime).filter(Showtime.showtime < now).all()
            )

            logger.info(f"found {len(past_showtimes)} old showtimes...")

            for showtime in past_showtimes:
                logger.info(
                    f"Deleting past showtime: {showtime.movie.name} at {showtime.theater.name}"
                )
                session.delete(showtime)  # Will cascade delete related notifications

            session.commit()
            logger.info("Database cleanup completed successfully")

        except Exception as e:
            session.rollback()
            logger.error(f"Error during database cleanup: {str(e)}")
