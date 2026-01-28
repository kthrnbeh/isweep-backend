# app/database.py
"""
Database setup and ORM models for ISweep.
"""

import os
from sqlalchemy import create_engine, Column, String, Boolean, Integer, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# SQLite database file
DB_PATH = os.getenv("ISWEEP_DB_PATH", "isweep.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=os.getenv("ISWEEP_DEBUG", "false").lower() == "true",
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# -------------------------------------------------
# ORM MODELS
# -------------------------------------------------
class PreferenceDB(Base):
    """Persistent preference record in database.
    
    Stores both the effective blocked_words AND the user's selections:
    - blocked_words: effective merged list (for backward compatibility and quick access)
    - selected_packs: JSON string of preset pack selections (e.g., '{"strong_profanity": true}')
    - custom_words: JSON string of user's custom words (e.g., '["word1", "word2"]')
    - caption_offset_ms: timing offset for captions (0-2000ms)
    """
    __tablename__ = "preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    category = Column(String, index=True)
    enabled = Column(Boolean, default=True)
    action = Column(String, default="none")
    duration_seconds = Column(Float, default=0.0)
    blocked_words = Column(String, default="")  # Effective merged list (comma-separated)
    selected_packs = Column(String, default="{}")  # JSON object of pack selections
    custom_words = Column(String, default="[]")  # JSON array of custom words
    caption_offset_ms = Column(Integer, default=300)  # Caption timing offset in ms

    def __repr__(self):
        return f"<PreferenceDB(user={self.user_id}, category={self.category})>"


def init_db():
    """Create all tables in the database."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Get a database session (for dependency injection in FastAPI)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
