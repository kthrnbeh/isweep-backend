"""Chunk transcription service for ISweep ASR (faster-whisper based)."""

import base64
import os
import tempfile
from typing import List, Dict, Optional

from faster_whisper import WhisperModel

WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")          # "cpu" or "cuda"
WHISPER_COMPUTE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")  # e.g. "int8", "float16"

model = WhisperModel(WHISPER_MODEL_SIZE, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE)


def transcribe_audio_chunk(
    audio_b64: str,
    user_id: str,
    chunk_start_seconds: Optional[float] = None,
):
    """Decode a base64 audio chunk, transcribe it with Whisper, and offset timestamps.

    Args:
        audio_b64: WebM/Opus audio payload encoded as base64.
        user_id: Identifier for logging/association.
        chunk_start_seconds: Absolute start time to add to segment timestamps.

    Returns:
        List of segment dicts with text, start_seconds, end_seconds.
    """
    temp_path = None
    try:
        audio_bytes = base64.b64decode(audio_b64)

        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as temp_audio:
            temp_audio.write(audio_bytes)
            temp_audio.flush()
            temp_path = temp_audio.name

        segments, info = model.transcribe(
            temp_path,
            beam_size=1,
            word_timestamps=False,  # cheaper; turn on only if you need it
            vad_filter=True,        # often helps for speech chunks
        )

        offset = float(chunk_start_seconds) if chunk_start_seconds is not None else 0.0

        out: List[Dict] = []
        for seg in segments:
            text = (seg.text or "").strip()
            if not text:
                continue
            out.append(
                {
                    "text": text,
                    "start_seconds": float(seg.start) + offset,
                    "end_seconds": float(seg.end) + offset,
                }
            )
        return out

    except Exception as e:
        print(f"[ASR] Transcription error (user_id={user_id}): {e}")
        return []

    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except Exception:
                # If Windows still has a handle open for any reason, don't crash the request
                pass
# Example usage:
# segments = transcribe_audio_chunk(audio_b64="...", user_id="user123")