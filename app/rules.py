# app/rules.py
"""
Decision engine and preference management.
Now uses SQLAlchemy ORM for persistence.
"""

from __future__ import annotations

import re
from typing import Optional
from sqlalchemy.orm import Session
from .models import Preference, Event, DecisionResponse, Action
from .database import PreferenceDB


# -------------------------------------------------
# DEFAULT PREFERENCES
# -------------------------------------------------
def _default_preferences_for_user(user_id: str) -> list[Preference]:
    """Default preferences when user has no custom config.
    
    Standardized category keys: language, violence, sexual
    """
    return [
        Preference(user_id=user_id, category="language", enabled=True, action=Action.mute, duration_seconds=0.5, blocked_words=[], caption_offset_ms=300),
        Preference(user_id=user_id, category="violence", enabled=True, action=Action.fast_forward, duration_seconds=10, blocked_words=[], caption_offset_ms=300),
        Preference(user_id=user_id, category="sexual", enabled=True, action=Action.skip, duration_seconds=30, blocked_words=[], caption_offset_ms=300),
    ]


# -------------------------------------------------
# DATABASE OPERATIONS
# -------------------------------------------------
def save_preference(db: Session, pref: Preference) -> None:
    """
    Save/overwrite a preference by user_id + category.
    """
    # Check if preference already exists
    existing = db.query(PreferenceDB).filter(
        PreferenceDB.user_id == pref.user_id,
        PreferenceDB.category == pref.category,
    ).first()

    import json
    
    if existing:
        # Update
        existing.enabled = pref.enabled
        existing.action = pref.action.value
        existing.duration_seconds = pref.duration_seconds
        existing.blocked_words = ",".join(pref.blocked_words)
        existing.selected_packs = json.dumps(pref.selected_packs)
        existing.custom_words = json.dumps(pref.custom_words)
        existing.caption_offset_ms = pref.caption_offset_ms
    else:
        # Insert
        db_pref = PreferenceDB(
            user_id=pref.user_id,
            category=pref.category,
            enabled=pref.enabled,
            action=pref.action.value,
            duration_seconds=pref.duration_seconds,
            blocked_words=",".join(pref.blocked_words),
            selected_packs=json.dumps(pref.selected_packs),
            custom_words=json.dumps(pref.custom_words),
            caption_offset_ms=pref.caption_offset_ms,
        )
        db.add(db_pref)

    db.commit()


def save_bulk_preferences(db: Session, user_id: str, preferences: dict[str, any]) -> None:
    """
    Save multiple preferences for a user in one transaction.
    preferences: dict mapping category -> {enabled, action, duration_seconds, blocked_words, selected_packs, custom_words, caption_offset_ms}
    """
    import json
    
    for category, pref_data in preferences.items():
        # Convert dict to Preference model
        pref = Preference(
            user_id=user_id,
            category=category,
            enabled=pref_data.get('enabled', True),
            action=Action(pref_data.get('action', 'none')),
            duration_seconds=pref_data.get('duration_seconds', 0.0),
            blocked_words=pref_data.get('blocked_words', []),
            selected_packs=pref_data.get('selected_packs', {}),
            custom_words=pref_data.get('custom_words', []),
            caption_offset_ms=int(pref_data.get('caption_offset_ms', 300)),
        )
        
        # Check if preference already exists
        existing = db.query(PreferenceDB).filter(
            PreferenceDB.user_id == user_id,
            PreferenceDB.category == category,
        ).first()

        if existing:
            # Update
            existing.enabled = pref.enabled
            existing.action = pref.action.value
            existing.duration_seconds = pref.duration_seconds
            existing.blocked_words = ",".join(pref.blocked_words)
            existing.selected_packs = json.dumps(pref.selected_packs)
            existing.custom_words = json.dumps(pref.custom_words)
            existing.caption_offset_ms = pref.caption_offset_ms
        else:
            # Insert
            db_pref = PreferenceDB(
                user_id=user_id,
                category=category,
                enabled=pref.enabled,
                action=pref.action.value,
                duration_seconds=pref.duration_seconds,
                blocked_words=",".join(pref.blocked_words),
                selected_packs=json.dumps(pref.selected_packs),
                custom_words=json.dumps(pref.custom_words),
                caption_offset_ms=pref.caption_offset_ms,
            )
            db.add(db_pref)
    
    db.commit()


def get_preference(db: Session, user_id: str, category: str) -> Optional[Preference]:
    """Retrieve a single preference."""
    db_pref = db.query(PreferenceDB).filter(
        PreferenceDB.user_id == user_id,
        PreferenceDB.category == category,
    ).first()

    if not db_pref:
        return None

    return _db_to_preference(db_pref)


def get_all_preferences(db: Session, user_id: str) -> dict[str, Preference]:
    """Get all preferences for a user, filling in defaults if needed."""
    db_prefs = db.query(PreferenceDB).filter(PreferenceDB.user_id == user_id).all()

    result = {}
    categories_found = set()

    for db_pref in db_prefs:
        pref = _db_to_preference(db_pref)
        result[pref.category] = pref
        categories_found.add(pref.category)

    # Add defaults for missing categories
    defaults = _default_preferences_for_user(user_id)
    for default_pref in defaults:
        if default_pref.category not in categories_found:
            result[default_pref.category] = default_pref

    return result


def _db_to_preference(db_pref: PreferenceDB) -> Preference:
    """Convert database record to Pydantic model."""
    import json
    
    blocked_words = [w.strip() for w in db_pref.blocked_words.split(",") if w.strip()] if db_pref.blocked_words else []
    
    # Parse JSON fields with fallback to defaults
    try:
        selected_packs = json.loads(db_pref.selected_packs) if hasattr(db_pref, 'selected_packs') and db_pref.selected_packs else {}
    except (json.JSONDecodeError, AttributeError):
        selected_packs = {}
    
    try:
        custom_words = json.loads(db_pref.custom_words) if hasattr(db_pref, 'custom_words') and db_pref.custom_words else []
    except (json.JSONDecodeError, AttributeError):
        custom_words = []
    
    # Get caption offset with fallback to default
    caption_offset_ms = int(db_pref.caption_offset_ms) if hasattr(db_pref, 'caption_offset_ms') and db_pref.caption_offset_ms is not None else 300
    
    return Preference(
        user_id=db_pref.user_id,
        category=db_pref.category,
        enabled=db_pref.enabled,
        action=Action(db_pref.action),
        duration_seconds=db_pref.duration_seconds,
        blocked_words=blocked_words,
        selected_packs=selected_packs,
        custom_words=custom_words,
        caption_offset_ms=caption_offset_ms,
    )


# -------------------------------------------------
# DECISION ENGINE
# -------------------------------------------------
def _find_blocked_word_match(db: Session, user_id: str, text: str) -> Optional[tuple[str, str, str]]:
    """
    Return (category, matched_word, regex_used) if any blocked word matches.
    Uses word-boundary regex matching to ensure exact phrase/word boundaries.
    Example:
      - "god" matches only as \bgod\b (standalone word, not inside other words)
      - "god almighty" matches only as \bgod\s+almighty\b (words in sequence)
    """
    prefs = get_all_preferences(db, user_id)
    text_lower = text.lower()

    for category, pref in prefs.items():
        if not pref.enabled:
            continue

        # Merge built-in blocked words with user-provided custom words.
        merged_words = list(pref.blocked_words) + list(pref.custom_words)

        for blocked_word in merged_words:
            if not blocked_word or not blocked_word.strip():
                continue
            
            w_clean = blocked_word.strip().lower()
            
            # Build regex pattern with word boundaries
            # Replace punctuation with flexible whitespace, keep word characters
            # Example: "god almighty" -> r'\bgod\s+almighty\b'
            # Example: "goddamn" -> r'\bgoddamn\b'
            
            # Escape special regex chars, but preserve word structure
            pattern = re.escape(w_clean)
            # Replace escaped spaces with flexible whitespace
            pattern = pattern.replace(r'\ ', r'\s+')
            # Add word boundaries at start and end
            pattern = r'\b' + pattern + r'\b'
            
            # Try to match the pattern in normalized text
            match = re.search(pattern, text_lower)
            if match:
                matched_substring = match.group(0)
                return (category, blocked_word, pattern)

    return None


def decide(db: Session, event: Event) -> DecisionResponse:
    """
    Main decision engine.
    Priority order:
      1) blocked word match (if any)
      2) content_type match + confidence threshold
      3) no action
    """
    # 1) Blocked words
    if event.text:
        hit = _find_blocked_word_match(db, event.user_id, event.text)
        if hit:
            category, word, regex_pattern = hit
            pref = get_preference(db, event.user_id, category)
            if pref and pref.enabled:
                return DecisionResponse(
                    action=pref.action,
                    duration_seconds=pref.duration_seconds,
                    reason=f"Blocked word match: '{word}' (regex: {regex_pattern})",
                    matched_category=category,
                    matched_term=word,
                )

    # 2) Content model category
    if event.content_type:
        pref = get_preference(db, event.user_id, event.content_type)
        if pref and pref.enabled:
            # Simple threshold you can tune later
            threshold = 0.70
            if event.confidence is None or event.confidence >= threshold:
                return DecisionResponse(
                    action=pref.action,
                    duration_seconds=pref.duration_seconds,
                    reason=f"Matched category '{event.content_type}' (confidence={event.confidence})",
                    matched_category=event.content_type,
                    matched_term=event.content_type,
                )

    # 3) No action needed
    return DecisionResponse(
        action=Action.none,
        duration_seconds=0,
        reason="No filter matched",
        matched_category=None,
        matched_term=None,
    )
