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
from datetime import datetime, timezone
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



class SeatNotification(Base):
    __tablename__ = "seat_notifications"

    id = Column(Integer, primary_key=True)
    user_email = Column(String(255), nullable=False)
    seat_number = Column(String(10), nullable=False)
    url = Column(String(60), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now(timezone.utc))
    show_date = Column(DateTime, nullable=False)

    __table_args__ = (UniqueConstraint("user_email", "url", "seat_number"),)
