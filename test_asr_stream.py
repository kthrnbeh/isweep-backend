"""Quick ASR stream smoke test for sending a WebM chunk to the backend."""

import base64
import requests


def load_audio_as_base64(path):
    """Read a binary audio file and return its base64-encoded string."""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

if __name__ == "__main__":
    # Path to a short WebM/Opus audio file (must exist)
    AUDIO_PATH = "test_audio.webm"
    audio_b64 = load_audio_as_base64(AUDIO_PATH)
    payload = {
        "user_id": "user123",
        "tab_id": 1,
        "seq": 1,
        "mime_type": "audio/webm",
        "audio_b64": audio_b64
    }
    response = requests.post(
        "http://127.0.0.1:8001/asr/stream",
        json=payload
    )
    print("Status:", response.status_code)
    print("Response:", response.json())
