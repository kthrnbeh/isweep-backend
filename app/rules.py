# app/rules.py
from __future__ import annotations

from typing import Dict, List, Optional
from .models import Preference, Event, DecisionResponse, Action


# ----------------------------
# In-memory storage (MVP)
# ----------------------------
# Keyed by category, e.g. "language", "sexual", "violence"
_PREFERENCES: Dict[str, Preference] = {}


def _default_preferences() -> Dict[str, Preference]:
    """Defaults used if user hasn't configured anything yet."""
    defaults = [
        Preference(category="language", enabled=True, action=Action.mute, duration_seconds=4, blocked_words=[]),
        Preference(category="sexual", enabled=True, action=Action.skip, duration_seconds=30, blocked_words=[]),
        Preference(category="violence", enabled=True, action=Action.fast_forward, duration_seconds=10, blocked_words=[]),
    ]
    return {p.category: p for p in defaults}


def save_preference(pref: Preference) -> None:
    """
    Store/overwrite a preference by category.
    Called by POST /preferences.
    """
    global _PREFERENCES
    if not _PREFERENCES:
        _PREFERENCES = _default_preferences()

    _PREFERENCES[pref.category] = pref


def _get_pref(category: str) -> Optional[Preference]:
    global _PREFERENCES
    if not _PREFERENCES:
        _PREFERENCES = _default_preferences()
    return _PREFERENCES.get(category)


def _find_blocked_word_match(text: str) -> Optional[tuple[str, str]]:
    """
    Return (category, matched_word) if any blocked word matches.
    We look through all enabled preferences' blocked_words.
    """
    lowered = text.lower()

    global _PREFERENCES
    if not _PREFERENCES:
        _PREFERENCES = _default_preferences()

    for category, pref in _PREFERENCES.items():
        if not pref.enabled:
            continue
        for w in pref.blocked_words:
            w2 = w.strip().lower()
            if w2 and w2 in lowered:
                return (category, w2)

    return None


def decide(event: Event) -> DecisionResponse:
    """
    Main decision engine.
    Priority order:
      1) blocked word match (if any)
      2) content_type match + confidence threshold
      3) no action
    """
    # 1) Blocked words
    if event.text:
        hit = _find_blocked_word_match(event.text)
        if hit:
            category, word = hit
            pref = _get_pref(category)
            if pref and pref.enabled:
                return DecisionResponse(
                    action=pref.action,
                    duration_seconds=pref.duration_seconds,
                    reason=f"Blocked word match: '{word}'",
                    matched_category=category,
                )

    # 2) Content model category
    if event.content_type:
        pref = _get_pref(event.content_type)
        if pref and pref.enabled:
            # Simple threshold you can tune later
            threshold = 0.70
            if event.confidence is None or event.confidence >= threshold:
                return DecisionResponse(
                    action=pref.action,
                    duration_seconds=pref.duration_seconds,
                    reason=f"Matched category '{event.content_type}' (confidence={event.confidence})",
                    matched_category=event.content_type,
                )

    # 3) Default: do nothing
    return DecisionResponse(
        action=Action.none,
        duration_seconds=0,
        reason="No match",
        matched_category=None,
    )
