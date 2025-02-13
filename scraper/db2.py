from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    Date,
    Time,
    Boolean,
    ForeignKey,
    UniqueConstraint,
)

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv


load_dotenv()

USER = os.getenv("user")
PASSWORD = os.getenv("password")
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")

DATABASE_URL = f"postgresql+psycopg2://{USER}.{HOST}:{PASSWORD}@aws-0-us-east-2.pooler.supabase.com:{PORT}/{DBNAME}"

engine = create_engine(
    DATABASE_URL,
)

try:
    with engine.connect() as connection:
        print("Connection successful!")
except Exception as e:
    print(f"Failed to connect: {e}")

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


Base = declarative_base()


class Theater(Base):
    __tablename__ = "theaters"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)

    theater_movie_dates = relationship("TheaterMovieDate", back_populates="theater")


class Movie(Base):
    __tablename__ = "movies"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    last_detected = Column(DateTime, nullable=False)

    theater_movie_dates = relationship("TheaterMovieDate", back_populates="movie")


# stores a movie in a theater on a date. For ex: Avengers in Empire 25 on Feb 10
class TheaterMovieDate(Base):
    __tablename__ = "theater_movie_dates"

    id = Column(Integer, primary_key=True)
    theater_id = Column(Integer, ForeignKey("theaters.id", ondelete="CASCADE"))
    movie_id = Column(Integer, ForeignKey("movies.id", ondelete="CASCADE"))
    show_date = Column(Date, nullable=False)

    theater = relationship("Theater", back_populates="theater_movie_dates")
    movie = relationship("Movie", back_populates="theater_movie_dates")
    movie_formats = relationship("MovieFormat", back_populates="theater_movie_date")

    __table_args__ = (UniqueConstraint("theater_id", "movie_id", "show_date"),)


class Format(Base):
    __tablename__ = "formats"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)

    movie_formats = relationship("MovieFormat", back_populates="format")


# stores a format for a movie in a theater on a date. For ex: Dolby for Avengers in Empire 25 on Feb 10
class MovieFormat(Base):
    __tablename__ = "movie_formats"

    id = Column(Integer, primary_key=True)
    theater_movie_date_id = Column(
        Integer, ForeignKey("theater_movie_dates.id", ondelete="CASCADE")
    )
    format_id = Column(Integer, ForeignKey("formats.id", ondelete="CASCADE"))

    theater_movie_date = relationship(
        "TheaterMovieDate", back_populates="movie_formats"
    )
    format = relationship("Format", back_populates="movie_formats")
    showtimes = relationship("Showtime", back_populates="movie_format")

    __table_args__ = (UniqueConstraint("theater_movie_date_id", "format_id"),)


# a showtime for a format for a movie in a theater on a date
class Showtime(Base):
    __tablename__ = "showtimes"

    id = Column(Integer, primary_key=True)
    movie_format_id = Column(
        Integer, ForeignKey("movie_formats.id", ondelete="CASCADE")
    )
    show_time = Column(Time, nullable=False)

    movie_format = relationship("MovieFormat", back_populates="showtimes")
    seat_notifications = relationship("SeatNotification", back_populates="showtime")

    __table_args__ = (UniqueConstraint("movie_format_id", "show_time"),)


class SeatNotification(Base):
    __tablename__ = "seat_notifications"

    id = Column(Integer, primary_key=True)
    user_email = Column(String(255), nullable=False)
    showtime_id = Column(Integer, ForeignKey("showtimes.id", ondelete="CASCADE"))
    seat_number = Column(String(10), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    showtime = relationship("Showtime", back_populates="seat_notifications")

    __table_args__ = (UniqueConstraint("user_email", "showtime_id", "seat_number"),)
