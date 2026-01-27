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
    user_id: str = Field(..., description="User identifier")
    category: str = Field(..., description="Filter category, e.g. language/sexual/violence")
    enabled: bool = True
    action: Action = Action.none
    duration_seconds: float = Field(default=0.0, ge=0, description="Duration in seconds")
    blocked_words: List[str] = Field(default_factory=list)

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user123",
                "category": "language",
                "enabled": True,
                "action": "mute",
                "duration_seconds": 4,
                "blocked_words": ["profanity1", "profanity2"]
            }
        }


class Event(BaseModel):
    user_id: str = Field(..., description="User identifier")
    text: Optional[str] = None
    content_type: Optional[str] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence score 0-1")
    timestamp_seconds: Optional[float] = None


class DecisionResponse(BaseModel):
    action: Action
    duration_seconds: float
    reason: str
    matched_category: Optional[str] = None
    matched_term: Optional[str] = None


class CategoryPreference(BaseModel):
    """Preference data for a single category (without user_id or category field)."""
    enabled: bool = True
    action: Action = Action.none
    duration_seconds: float = Field(default=0.0, ge=0, description="Duration in seconds")
    blocked_words: List[str] = Field(default_factory=list)


class BulkPreferences(BaseModel):
    """Bulk preference update for all categories."""
    user_id: str = Field(..., description="User identifier")
    preferences: dict[str, CategoryPreference] = Field(..., description="Preferences by category")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user123",
                "preferences": {
                    "language": {
                        "enabled": True,
                        "action": "mute",
                        "duration_seconds": 4,
                        "blocked_words": ["word1", "word2"]
                    },
                    "violence": {
                        "enabled": True,
                        "action": "skip",
                        "duration_seconds": 10,
                        "blocked_words": []
                    }
                }
            }
        }
