from datetime import datetime, timezone
import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
os.makedirs(DATABASE_DIR, exist_ok=True)
DATABASE_URL = f"sqlite:///{os.path.join(DATABASE_DIR, 'music_organizer.db')}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class MoodHistory(Base):
    """Stores user mood decisions and playlist selections to power personalization."""

    __tablename__ = "mood_history"

    id = Column(Integer, primary_key=True, index=True)
    song_id = Column(String, index=True, nullable=False)
    song_title = Column(String, nullable=False)
    artist = Column(String, nullable=False)
    user_mood = Column(String, nullable=True)
    ai_mood = Column(String, nullable=False)
    recommended_playlist = Column(String, nullable=False)
    selected_playlist = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


def init_db() -> None:
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
