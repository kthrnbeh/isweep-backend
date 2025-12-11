# app/models.py
from enum import Enum
from pydantic import BaseModel
from typing import Optional, List


class ContentType(str, Enum):
    language = "language"   # swearing, profanity
    violence = "violence"
    sexual = "sexual"
    other = "other"


class Action(str, Enum):
    none = "none"
    mute = "mute"
    skip = "skip"
    fast_forward = "fast_forward"


class Preference(BaseModel):
    """
    A single user rule:
    e.g. For sexual content -> skip 20 seconds.
    """
    user_id: str
    content_type: ContentType
    action: Action
    duration_seconds: Optional[float] = None
    enabled: bool = True
    # NEW: list of words/phrases that should trigger this preference
    blocked_words: Optional[list[str]] = None


class Event(BaseModel):
    user_id: str
    timestamp: float
    source: str
    text: Optional[str] = None
    content_type: Optional[ContentType] = None
    confidence: Optional[float] = None
    manual_override: bool = False


class DecisionResponse(BaseModel):
    action: Action
    duration_seconds: Optional[float] = None
    show_icon: bool = False
    reason: Optional[str] = None
class UserSettings(BaseModel):
    user_id: str
    preferences: List[Preference] = []  # List of user preferences          
# In-memory storage for preferences
_preferences: dict[tuple[str, str], Preference] = {}
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