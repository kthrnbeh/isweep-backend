
import base64
import tempfile
import os
from typing import List, Dict
from faster_whisper import WhisperModel

# You can choose 'small', 'medium', or 'large' for better accuracy (but slower/larger)
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base")

# Load model once at startup (CPU only by default, set device="cuda" for GPU)
model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")

def transcribe_audio_chunk(audio_b64: str, user_id: str) -> List[Dict]:
    """
    Transcribe audio chunk using faster-whisper (local, no API key)
    Args:
        audio_b64: Base64-encoded audio (WebM/Opus format)
        user_id: User ID for tracking
    Returns:
        List of segments with text and timestamps
    """
    try:
        # Decode base64 to bytes
        audio_bytes = base64.b64decode(audio_b64)
        # Write to temp file
        with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as temp_audio:
            temp_audio.write(audio_bytes)
            temp_audio.flush()
            temp_path = temp_audio.name
        # Transcribe
        segments, info = model.transcribe(temp_path, beam_size=1, word_timestamps=True)
        os.unlink(temp_path)
        # Convert to our segment format
        out = []
        for seg in segments:
            out.append({
                "text": seg.text.strip(),
                "start_seconds": float(seg.start),
                "end_seconds": float(seg.end)
            })
        return out
    except Exception as e:
        print(f"[ASR] Transcription error: {e}")
        return []
