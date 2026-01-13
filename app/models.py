# app/models.py
from __future__ import annotations

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class Action(str, Enum):
    none = "none"
    mute = "mute"
    skip = "skip"
    fast_forward = "fast_forward"


class Preference(BaseModel):
    category: str = Field(..., description="Filter category, e.g. language/sexual/violence")
    enabled: bool = True
    action: Action = Action.none
    duration_seconds: int = 0
    blocked_words: List[str] = Field(default_factory=list)


class Event(BaseModel):
    text: Optional[str] = None
    content_type: Optional[str] = None
    confidence: Optional[float] = None
    timestamp_seconds: Optional[float] = None


class DecisionResponse(BaseModel):
    action: Action
    duration_seconds: int
    reason: str
    matched_category: Optional[str] = None
