# tests/test_rules.py
"""
Unit tests for the decision engine and preference management.
Run with: pytest
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Preference, Event, Action
from app.database import Base, PreferenceDB
from app import rules


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()


class TestPreferenceManagement:
    def test_save_preference(self, db_session):
        """Test saving a preference."""
        pref = Preference(
            user_id="user123",
            category="language",
            enabled=True,
            action=Action.mute,
            duration_seconds=5,
            blocked_words=["bad1", "bad2"],
        )
        rules.save_preference(db_session, pref)

        # Verify it was saved
        retrieved = rules.get_preference(db_session, "user123", "language")
        assert retrieved is not None
        assert retrieved.user_id == "user123"
        assert retrieved.category == "language"
        assert retrieved.action == Action.mute
        assert len(retrieved.blocked_words) == 2

    def test_get_all_preferences_with_defaults(self, db_session):
        """Test that missing categories get defaults."""
        # Don't save anything, just retrieve
        prefs = rules.get_all_preferences(db_session, "user456")

        # Should have default categories
        assert "language" in prefs
        assert "sexual" in prefs
        assert "violence" in prefs
        assert prefs["language"].action == Action.mute

    def test_update_preference(self, db_session):
        """Test updating an existing preference."""
        # Save initial
        pref1 = Preference(
            user_id="user789",
            category="violence",
            enabled=True,
            action=Action.mute,
            duration_seconds=3,
            blocked_words=[],
        )
        rules.save_preference(db_session, pref1)

        # Update
        pref2 = Preference(
            user_id="user789",
            category="violence",
            enabled=False,
            action=Action.skip,
            duration_seconds=60,
            blocked_words=[],
        )
        rules.save_preference(db_session, pref2)

        # Verify update
        retrieved = rules.get_preference(db_session, "user789", "violence")
        assert retrieved.enabled is False
        assert retrieved.action == Action.skip
        assert retrieved.duration_seconds == 60


class TestDecisionEngine:
    def test_blocked_word_match(self, db_session):
        """Test that blocked words trigger the correct action."""
        # Set up a preference with a blocked word
        pref = Preference(
            user_id="user_test",
            category="language",
            enabled=True,
            action=Action.mute,
            duration_seconds=5,
            blocked_words=["profanity"],
        )
        rules.save_preference(db_session, pref)

        # Create an event with the blocked word
        event = Event(
            user_id="user_test",
            text="This contains profanity in it",
            content_type=None,
        )

        decision = rules.decide(db_session, event)
        assert decision.action == Action.mute
        assert decision.duration_seconds == 5
        assert decision.matched_category == "language"
        assert "Blocked word" in decision.reason

    def test_content_type_match_with_confidence(self, db_session):
        """Test that content type with sufficient confidence triggers action."""
        event = Event(
            user_id="user_test",
            text=None,
            content_type="sexual",
            confidence=0.85,  # Above default threshold of 0.70
        )

        decision = rules.decide(db_session, event)
        assert decision.action == Action.skip
        assert decision.matched_category == "sexual"

    def test_content_type_below_threshold(self, db_session):
        """Test that low confidence doesn't trigger action."""
        event = Event(
            user_id="user_test",
            text=None,
            content_type="sexual",
            confidence=0.50,  # Below threshold
        )

        decision = rules.decide(db_session, event)
        assert decision.action == Action.none
        assert decision.reason == "No filter matched"

    def test_disabled_preference_ignored(self, db_session):
        """Test that disabled preferences are skipped."""
        pref = Preference(
            user_id="user_test",
            category="language",
            enabled=False,  # Disabled
            action=Action.mute,
            duration_seconds=5,
            blocked_words=["profanity"],
        )
        rules.save_preference(db_session, pref)

        event = Event(
            user_id="user_test",
            text="This contains profanity",
            content_type=None,
        )

        decision = rules.decide(db_session, event)
        assert decision.action == Action.none

    def test_no_match_returns_none(self, db_session):
        """Test that no match returns Action.none."""
        event = Event(
            user_id="user_test",
            text="Clean text",
            content_type=None,
        )

        decision = rules.decide(db_session, event)
        assert decision.action == Action.none
        assert decision.duration_seconds == 0
