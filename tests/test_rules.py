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
        # First, set up a sexual preference with skip action
        pref = Preference(
            user_id="user_test",
            category="sexual",
            enabled=True,
            action=Action.skip,
            duration_seconds=30,
            blocked_words=[],
        )
        rules.save_preference(db_session, pref)

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

    def test_blocked_word_with_special_characters(self, db_session):
        """Test that blocked words match even with special characters in text."""
        pref = Preference(
            user_id="user_special",
            category="language",
            enabled=True,
            action=Action.mute,
            duration_seconds=5,
            blocked_words=["don't", "can't"],
        )
        rules.save_preference(db_session, pref)

        # Test with same special characters
        event = Event(
            user_id="user_special",
            text="You don't understand",
            content_type=None,
        )
        decision = rules.decide(db_session, event)
        assert decision.action == Action.mute
        assert "Blocked word" in decision.reason

    def test_blocked_word_word_boundary_no_partial_match(self, db_session):
        """Test that blocked words don't match as substrings."""
        pref = Preference(
            user_id="user_boundary",
            category="language",
            enabled=True,
            action=Action.mute,
            duration_seconds=5,
            blocked_words=["cat"],
        )
        rules.save_preference(db_session, pref)

        # "cat" should NOT match in "scatter" or "category"
        event = Event(
            user_id="user_boundary",
            text="The scatter plot shows categories",
            content_type=None,
        )
        decision = rules.decide(db_session, event)
        assert decision.action == Action.none

        # "cat" SHOULD match when it's a standalone word
        event2 = Event(
            user_id="user_boundary",
            text="The cat is here",
            content_type=None,
        )
        decision2 = rules.decide(db_session, event2)
        assert decision2.action == Action.mute

    def test_blocked_word_case_insensitive(self, db_session):
        """Test that matching is case-insensitive."""
        pref = Preference(
            user_id="user_case",
            category="language",
            enabled=True,
            action=Action.mute,
            duration_seconds=5,
            blocked_words=["PROFANITY"],
        )
        rules.save_preference(db_session, pref)

        # Different cases should all match
        for text in ["profanity", "PROFANITY", "Profanity", "pRoFaNiTy"]:
            event = Event(user_id="user_case", text=text, content_type=None)
            decision = rules.decide(db_session, event)
            assert decision.action == Action.mute, f"Failed for: {text}"

    def test_multiple_blocked_words(self, db_session):
        """Test that any blocked word triggers action."""
        pref = Preference(
            user_id="user_multi",
            category="language",
            enabled=True,
            action=Action.mute,
            duration_seconds=5,
            blocked_words=["damn", "hell", "crap"],
        )
        rules.save_preference(db_session, pref)

        # Test each word
        for word in ["damn", "hell", "crap"]:
            event = Event(
                user_id="user_multi",
                text=f"This is so {word}",
                content_type=None,
            )
            decision = rules.decide(db_session, event)
            assert decision.action == Action.mute, f"Failed for word: {word}"
            assert decision.duration_seconds == 5, f"Wrong duration for word: {word}"

    def test_custom_words_are_included_in_matching(self, db_session):
        """Test that custom_words are included in blocked word matching."""
        pref = Preference(
            user_id="user_custom",
            category="language",
            enabled=True,
            action=Action.mute,
            duration_seconds=5,
            blocked_words=[],
            custom_words=["unwanted"],
        )
        rules.save_preference(db_session, pref)

        event = Event(
            user_id="user_custom",
            text="This contains unwanted content",
            content_type=None,
        )
        decision = rules.decide(db_session, event)

        assert decision.action == Action.mute
        assert decision.matched_category == "language"
        assert decision.matched_term == "unwanted"

    def test_custom_word_word_boundary_no_false_positive(self, db_session):
        """Test custom word boundaries: 'ass' should not match 'class'."""
        pref = Preference(
            user_id="user_custom_boundary",
            category="language",
            enabled=True,
            action=Action.mute,
            duration_seconds=5,
            blocked_words=[],
            custom_words=["ass"],
        )
        rules.save_preference(db_session, pref)

        # Should NOT match inside other words
        event = Event(
            user_id="user_custom_boundary",
            text="This is a class assignment",
            content_type=None,
        )
        decision = rules.decide(db_session, event)
        assert decision.action == Action.none

        # SHOULD match standalone word
        event2 = Event(
            user_id="user_custom_boundary",
            text="That was ass",
            content_type=None,
        )
        decision2 = rules.decide(db_session, event2)
        assert decision2.action == Action.mute
        assert decision2.matched_term == "ass"
