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
    func,
    CheckConstraint,
)

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime, timezone
import os
from dotenv import load_dotenv
import pytz


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
    name = Column(String(255), nullable=False)
    timezone = Column(String(50), nullable=False)

    __table_args__ = (
        CheckConstraint(
            f"timezone = ANY(ARRAY{list(pytz.all_timezones)})", name="valid_timezone"
        ),
    )

    showtimes = relationship(
        "Showtime", back_populates="theater", cascade="all, delete"
    )


class Movie(Base):
    __tablename__ = "movies"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    last_detected = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    showtimes = relationship("Showtime", back_populates="movie", cascade="all, delete")


class Showtime(Base):
    __tablename__ = "showtimes"

    id = Column(Integer, primary_key=True)
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=False)
    theater_id = Column(Integer, ForeignKey("theaters.id"), nullable=False)
    showtime = Column(DateTime(timezone=True), nullable=False)
    seating_url = Column(String(60), nullable=False)

    movie = relationship("Movie", back_populates="showtimes")
    theater = relationship("Theater", back_populates="showtimes")
    seat_notifications = relationship(
        "SeatNotification", back_populates="showtime", cascade="all, delete"
    )


class SeatNotification(Base):
    __tablename__ = "seat_notifications"

    id = Column(Integer, primary_key=True)
    user_email = Column(String(255), nullable=False)
    seat_number = Column(String(20), nullable=False)
    showtime_id = Column(Integer, ForeignKey("showtimes.id"), nullable=False)
    last_notified = Column(DateTime(timezone=True), nullable=True)
    is_specifically_requested = Column(Boolean, nullable=False)

    showtime = relationship("Showtime", back_populates="seat_notifications")
