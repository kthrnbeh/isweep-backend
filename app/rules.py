# app/rules.py
# -------------------------------------------------
# Very simple in-memory "database" of preferences
# and a function to turn Events into Decisions.
# -------------------------------------------------

from typing import Dict, Tuple

from .models import Preference, Event, DecisionResponse, Action, ContentType


# Key: (user_id, content_type) -> Preference
_preferences: Dict[Tuple[str, str], Preference] = {}


def save_preference(pref: Preference) -> None:
    """Save or update a user's preference in memory."""
    key = (pref.user_id, pref.content_type.value)
    _preferences[key] = pref


def get_preference(user_id: str, content_type: str) -> Preference | None:
    """Look up a preference for a given user and content type."""
    return _preferences.get((user_id, content_type))


def _infer_content_type_from_text(event: Event) -> None:
    """
    If no content_type is provided, try to infer it from event.text
    using any language preferences and their blocked_words.
    """
    if event.content_type or not event.text:
        return

    lowered = event.text.lower()

    # Look for a language preference for this user that has blocked_words
    for (user_id, ctype), pref in _preferences.items():
        if user_id != event.user_id:
            continue
        if pref.content_type != ContentType.language:
            continue
        if not pref.blocked_words:
            continue

        for word in pref.blocked_words:
            if word.lower() in lowered:
                event.content_type = ContentType.language
                event.confidence = 1.0
                return


def decide(event: Event) -> DecisionResponse:
    """
    Core decision engine:
    - checks user preferences
    - checks confidence
    - returns an Action & whether to show the broom icon
    """

    # Default: do nothing
    decision = DecisionResponse(
        action=Action.none,
        duration_seconds=None,
        show_icon=False,
        reason="No matching preference or low confidence.",
    )

    # Manual override means: user clicked something like "skip now".
    if event.manual_override:
        decision.action = Action.skip
        decision.duration_seconds = 10.0
        decision.show_icon = True
        decision.reason = "Manual override from user."
        return decision

    # Try to infer content_type from text + blocked_words
    _infer_content_type_from_text(event)

    # If we still don't know content type, we can't apply rules yet.
    if not event.content_type:
        decision.reason = "No content_type provided or inferred."
        return decision

    # Optional: require a minimum confidence threshold
    if event.confidence is not None and event.confidence < 0.75:
        decision.reason = f"Confidence {event.confidence} below threshold."
        return decision

    pref = get_preference(event.user_id, event.content_type.value)
    if not pref or not pref.enabled:
        decision.reason = "No enabled preference for this content type."
        return decision

    # Apply user's preference
    decision.action = pref.action
    decision.duration_seconds = pref.duration_seconds
    decision.show_icon = True
    decision.reason = f"Matched preference for {event.content_type.value}."

    return decision
        """
        Combine global blocked words into language preference.
        """
        effective_prefs = []
        for (user_id, ctype), pref in _preferences.items():
            if user_id != self.user_id:
                continue
            if ctype == ContentType.language.value:
                # Merge global blocked words
                combined_blocked = set(pref.blocked_words or [])
                combined_blocked.update(self.blocked_words)
                pref.blocked_words = list(combined_blocked)
            effective_prefs.append(pref)
        return effective_prefs                  
    blocked_words=[word], enabled=True