import base64
import io
import tempfile
from openai import OpenAI
from typing import List, Dict
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def transcribe_audio_chunk(audio_b64: str, user_id: str) -> List[Dict]:
    """
    Transcribe audio chunk using OpenAI Whisper API
    Args:
        audio_b64: Base64-encoded audio (WebM/Opus format)
        user_id: User ID for tracking
    Returns:
        List of segments with text and timestamps
    """
    try:
        # Decode base64 to bytes
        audio_bytes = base64.b64decode(audio_b64)
        # Whisper API needs a file-like object
        # Create temporary file
        with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as temp_audio:
            temp_audio.write(audio_bytes)
            temp_audio.flush()
            temp_path = temp_audio.name
        # Transcribe using Whisper API
        with open(temp_path, 'rb') as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="verbose_json",
                timestamp_granularities=["segment"]
            )
        # Clean up temp file
        os.unlink(temp_path)
        # Convert to our segment format
        segments = []
        for segment in transcript.segments:
            segments.append({
                "text": segment.text.strip(),
                "start_seconds": segment.start,
                "end_seconds": segment.end
            })
        return segments
    except Exception as e:
        print(f"[ASR] Transcription error: {e}")
        return []
