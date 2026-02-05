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
    category: str = Field(..., description="Filter category: language, violence, or sexual (standardized keys)")
    enabled: bool = True
    action: Action = Action.none
    duration_seconds: float = Field(default=0.0, ge=0, description="Duration in seconds")
    blocked_words: List[str] = Field(default_factory=list, description="Effective merged blocked words")
    selected_packs: dict = Field(default_factory=dict, description="Preset pack selections (e.g., {'strong_profanity': true})")
    custom_words: List[str] = Field(default_factory=list, description="User's custom words")
    caption_offset_ms: int = Field(default=300, ge=-1000, le=2000, description="Caption timing offset in milliseconds (-1000 to +2000ms; negative = premute)")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user123",
                "category": "language",
                "enabled": True,
                "action": "mute",
                "duration_seconds": 4,
                "blocked_words": ["profanity1", "profanity2"],
                "selected_packs": {"strong_profanity": True},
                "custom_words": ["myword"],
                "caption_offset_ms": 300
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
    blocked_words: List[str] = Field(default_factory=list, description="Effective merged blocked words")
    selected_packs: dict = Field(default_factory=dict, description="Preset pack selections")
    custom_words: List[str] = Field(default_factory=list, description="User's custom words")
    caption_offset_ms: int = Field(default=300, ge=-1000, le=2000, description="Caption timing offset in milliseconds (-1000 to +2000ms; negative = premute)")


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


# -------------------------------------------------
# ASR (AUTOMATIC SPEECH RECOGNITION) MODELS
# -------------------------------------------------
class AudioChunk(BaseModel):
    """Audio chunk from extension."""
    user_id: str = Field(..., description="User identifier")
    tab_id: int = Field(..., description="Chrome tab ID")
    seq: int = Field(..., description="Sequence number of this chunk")
    mime_type: str = Field(..., description="Audio MIME type (e.g., 'audio/webm;codecs=opus')")
    audio_b64: str = Field(..., description="Base64-encoded audio data")
    chunk_start_seconds: Optional[float] = Field(
        default=None,
        ge=0,
        description="Absolute start time of this chunk on the media timeline (seconds)",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user123",
                "tab_id": 123,
                "seq": 1,
                "mime_type": "audio/webm;codecs=opus",
                "audio_b64": "GkXfo59...",
                "chunk_start_seconds": 12.3
            }
        }


class TranscriptSegment(BaseModel):
    """Transcribed audio segment with timing."""
    text: str = Field(..., description="Transcribed text")
    start_seconds: float = Field(..., ge=0, description="Segment start time in seconds")
    end_seconds: float = Field(..., ge=0, description="Segment end time in seconds")
    confidence: float = Field(default=0.9, ge=0.0, le=1.0, description="Confidence score 0-1")
    is_blocked: bool = Field(default=False, description="True if this segment matched a blocked word")
    blocked_word: Optional[str] = Field(default=None, description="The blocked word that matched, if any")
    category: Optional[str] = Field(default=None, description="The preference category that matched, if any")


class ASRStreamResponse(BaseModel):
    """Response from /asr/stream endpoint."""
    segments: List[TranscriptSegment] = Field(default_factory=list, description="Transcribed segments")
