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
