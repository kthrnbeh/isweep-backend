# app/models.py
# ------------------------------------------------------------
# This file defines ALL DATA STRUCTURES used by the ISweep backend.
#
# These classes describe:
#   - user settings (preferences)
#   - incoming events (subtitle lines, etc.)
#   - output decisions (mute, skip, FF)
#
# FastAPI uses Pydantic BaseModel classes to VALIDATE and PARSE
# all JSON received from the frontend.
#
# Example:
#   When the frontend sends:
#      {"action": "mute"}
#   Pydantic ensures:
#      - valid fields
#      - correct types
#      - converts strings → Enums
#
# This file is the “language” that the frontend and backend share.
# ------------------------------------------------------------

"""Pydantic models and in-memory preference store for the ISweep backend."""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel



# ------------------------------------------------------------
# ENUM: ContentType
# ------------------------------------------------------------
class ContentType(str, Enum):
    """
    An enumeration of WHAT KIND of content was detected or filtered.

    These categories match what appears in Settings:
      - language = profanity / swearing
      - violence = gory or harmful scenes
      - sexual   = nudity / intimacy
      - other    = future expansion (drug use, crude jokes, etc.)

    Using Enum gives ISweep structured, predictable category labels.
    """
    language = "language"
    violence = "violence"
    sexual = "sexual"
    other = "other"


# ------------------------------------------------------------
# ENUM: Action
# ------------------------------------------------------------
class Action(str, Enum):
    """
    Represents WHAT ISweep should do when bad content is detected.
    These are the allowed actions returned from backend → frontend.
    """
    none = "none"                 # Do nothing; allow playback normally
    mute = "mute"                 # Temporarily silence audio
    skip = "skip"                 # Jump ahead N seconds
    fast_forward = "fast_forward" # Speed up playback for N seconds


# ------------------------------------------------------------
# MODEL: Preference
# ------------------------------------------------------------
class Preference(BaseModel):
    """
    Represents a single rule set by a user.

    Every Preference answers:
        "When ISweep detects X, what do you want it to do?"

    Example:
        If content_type = sexual
        and action = skip
        and duration_seconds = 20

    Meaning:
        When a sexual scene is detected, skip ahead 20 seconds.
    """

    user_id: str
    # Identifies which user the preference belongs to.
    # Multiple users (profiles) can exist eventually.

    content_type: ContentType
    # Which category does this preference apply to?
    # Example: profanity = ContentType.language

    action: Action
    # What ISweep should do: mute/skip/fast_forward/none

    duration_seconds: Optional[float] = None
    # How long the action should last.
    # Example: mute for 4 seconds; skip ahead 15 seconds.

    enabled: bool = True
    # Whether this preference is active. Useful for parental lock toggles.

    blocked_words: Optional[List[str]] = None
    """
    A list of specific trigger words for language filtering.
    Example:
        ["badword", "dummy", "oh my god"]

    If Event.text contains any of these words,
    the backend will infer the content_type = language
    and apply this preference.
    """


# ------------------------------------------------------------
# MODEL: Event
# ------------------------------------------------------------
class Event(BaseModel):
    """
    Represents REAL-TIME information sent from the frontend.

    The frontend sends an Event whenever:
      - A subtitle appears
      - AI speech-to-text detects something
      - A scene detection model flags content

    The backend analyzes the Event and decides what to do.
    """

    user_id: str
    # Which user the event belongs to (matched to preferences)

    timestamp: float
    # The current timestamp in the user's video.
    # Example: 125.3 = viewer is at 2 minutes, 5.3 seconds.

    source: str
    # Where the event came from:
    #   "browser", "extension", "tv", "mobile", etc.

    text: Optional[str] = None
    # Subtitle line, transcript text, or AI detection text.

    content_type: Optional[ContentType] = None
    # Sometimes the frontend knows the category already.
    # If None, the backend tries to infer from text and preferences.

    confidence: Optional[float] = None
    # Used in future expansions for AI models.
    # Example: profanity model returns confidence=0.88.

    manual_override: bool = False
    # Allows future override controls (user-skip button, etc.)
    # Not used yet but builds toward full remote-control logic.
    


# ------------------------------------------------------------
# MODEL: DecisionResponse
# ------------------------------------------------------------
class DecisionResponse(BaseModel):
    """
    Represents WHAT the backend tells the frontend to do.

    This is the response to /event.

    Example:
      {
        "action": "mute",
        "duration_seconds": 4,
        "show_icon": true,
        "reason": "Detected blocked word: 'dummy'"
      }

    The frontend receives this and applies it to the actual video.
    """

    action: Action                        # mute / skip / fast_forward / none
    duration_seconds: Optional[float] = None  # how long the action lasts
    show_icon: bool = False               # whether to show broom icon
    reason: Optional[str] = None          # explanation, useful for logs/UI


# ------------------------------------------------------------
# MODEL: UserSettings
# ------------------------------------------------------------
class UserSettings(BaseModel):
    """
    Wraps all preferences belonging to a single user.

    Not used heavily yet, but allows:
      - Syncing Settings page → backend
      - Exporting/importing user preferences
      - Multi-profile support
    """
    user_id: str
    preferences: List[Preference] = []


# ------------------------------------------------------------
# IN-MEMORY PREFERENCE STORAGE
# ------------------------------------------------------------
_preferences: dict[tuple[str, str], Preference] = {}
"""
This dictionary stores preferences for all users.

KEY SHAPE:
    (user_id, content_type)

VALUE:
    Preference object

Example:
    _preferences[("user123", "language")] = Preference(...)

Why a dictionary?
    - Fast lookups
    - Simple for development
    - No database needed (yet)

Later we replace this with:
    - SQLite
    - PostgreSQL
    - Redis
"""


# ------------------------------------------------------------
# SAVE PREFERENCE
# ------------------------------------------------------------
def save_preference(pref: Preference) -> None:
    """
    Save or update a user's preference in memory.

    Called when the frontend posts to /preferences.

    Example:
        key = ("user123", "language")
        value = Preference(...)
    """
    key = (pref.user_id, pref.content_type.value)
    _preferences[key] = pref


# ------------------------------------------------------------
# GET PREFERENCE
# ------------------------------------------------------------
def get_preference(user_id: str, content_type: str) -> Preference | None:
    """
    Retrieve a preference for a given user + category.

    Used by rules.decide() when applying logic:
      - check profanity settings?
      - check sexual content settings?

    If no preference exists, return None.
    """
    return _preferences.get((user_id, content_type))


# ------------------------------------------------------------
# CONTENT TYPE INFERENCE (LANGUAGE)
# ------------------------------------------------------------
def _infer_content_type_from_text(event: Event) -> None:
    """
    If the event did NOT specify content_type,
    try to guess it from the text using user-defined blocked words.

    This function:
      - converts text to lowercase
      - loops through all preferences for this user
      - if a blocked word is found →
            decide this event is "language"

    This enables:
      - dynamic detection
      - profanity filtering without AI model
      - immediate results from subtitles

    Example:
        event.text = "Oh my God!"
        blocked_words = ["oh my god"]

        → event.content_type = ContentType.language
        → event.confidence = 1.0
    """

    # If event already has type or lacks text → do nothing
    if event.content_type or not event.text:
        return

    lowered = event.text.lower()

   
    # Search all preferences belonging to this user
    for (user_id, _), pref in _preferences.items():
        if user_id != event.user_id:
            continue

        # Only language category supports text-based inference
        if pref.content_type != ContentType.language:
            continue

        # Skip if no blocked_words defined
        if not pref.blocked_words:
            continue

        # If any blocked word is in the subtitle text → mark event
        for word in pref.blocked_words:
            if word.lower() in lowered:
                event.content_type = ContentType.language
                event.confidence = 1.0  # certainty because match is exact
                return
