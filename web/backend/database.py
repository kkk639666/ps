from sqlalchemy import Column, Integer, String, Float, DateTime, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timezone

from config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def _utcnow():
    return datetime.now(timezone.utc)


class HistoryRecord(Base):
    __tablename__ = "history"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=_utcnow)
    filename = Column(String(255))
    result_type = Column(String(50))  # pest / disease / healthy / error
    label = Column(String(255))
    label_zh = Column(String(255))
    confidence = Column(Float)
    elapsed_ms = Column(Float)
    input_path = Column(String(500))
    output_path = Column(String(500))
    extra = Column(Text)  # JSON string for boxes etc.


def create_tables():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
