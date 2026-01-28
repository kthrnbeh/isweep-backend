# app/database.py
"""
Database setup and ORM models for ISweep.
"""

import os
import logging
from sqlalchemy import create_engine, Column, String, Boolean, Integer, Float, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

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


def migrate_db():
    """Add missing columns to existing database tables."""
    inspector = inspect(engine)
    
    # Check if preferences table exists
    if 'preferences' not in inspector.get_table_names():
        logger.info("Preferences table doesn't exist yet, will be created by init_db()")
        return
    
    # Get existing columns
    existing_columns = {col['name'] for col in inspector.get_columns('preferences')}
    logger.info(f"Existing columns in preferences table: {existing_columns}")
    
    # Add caption_offset_ms column if missing
    if 'caption_offset_ms' not in existing_columns:
        logger.info("Adding caption_offset_ms column to preferences table...")
        with engine.connect() as conn:
            conn.execute(text('ALTER TABLE preferences ADD COLUMN caption_offset_ms INTEGER DEFAULT 300'))
            conn.commit()
        logger.info("✅ Added caption_offset_ms column")
    else:
        logger.info("caption_offset_ms column already exists")


def init_db():
    """Create all tables in the database and run migrations."""
    Base.metadata.create_all(bind=engine)
    migrate_db()


def get_db():
    """Get a database session (for dependency injection in FastAPI)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
