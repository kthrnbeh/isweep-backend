# app/asr.py
"""
Automatic Speech Recognition (ASR) module for ISweep backend.

INSTALLATION NOTES:
  faster-whisper is recommended for production:
  $ pip install faster-whisper

  Alternative (lighter weight but lower quality):
  $ pip install vosk

This module handles:
  1. Audio chunk buffering per (user_id, tab_id)
  2. Whisper-based transcription
  3. Timed segment extraction and confidence scoring
"""

import base64
import io
import threading
from collections import defaultdict
from typing import List, Optional, Tuple
from datetime import datetime

from .models import TranscriptSegment


# =========================================================
# GLOBAL STATE: Rolling buffer per (user_id, tab_id)
# =========================================================
class AudioBuffer:
    """In-memory rolling buffer for audio chunks."""
    
    def __init__(self, max_chunks: int = 10):
        """
        Args:
            max_chunks: Maximum chunks to keep in memory per session.
                       Chunks are processed in batches of N chunks (e.g., 3-4),
                       so keeping 10 allows ~3 ASR runs before oldest is pruned.
        """
        self.max_chunks = max_chunks
        self.chunks: List[Tuple[int, bytes]] = []  # (seq, audio_bytes)
        self.lock = threading.Lock()
    
    def add_chunk(self, seq: int, audio_bytes: bytes) -> None:
        """Add a chunk to the buffer."""
        with self.lock:
            self.chunks.append((seq, audio_bytes))
            # Prune if over limit
            if len(self.chunks) > self.max_chunks:
                self.chunks = self.chunks[-self.max_chunks:]
    
    def get_all_bytes(self) -> Optional[bytes]:
        """Concatenate all chunks into single audio bytes (for Whisper)."""
        with self.lock:
            if not self.chunks:
                return None
            # Simple concatenation (works for most audio formats)
            return b''.join(audio_bytes for _, audio_bytes in self.chunks)
    
    def get_and_clear(self) -> Optional[bytes]:
        """Get all bytes and clear buffer."""
        with self.lock:
            if not self.chunks:
                return None
            audio_bytes = b''.join(audio_bytes for _, audio_bytes in self.chunks)
            self.chunks = []
            return audio_bytes
    
    def clear(self) -> None:
        """Clear the buffer."""
        with self.lock:
            self.chunks = []


# Global buffer store: {(user_id, tab_id): AudioBuffer}
_audio_buffers = defaultdict(lambda: AudioBuffer(max_chunks=10))
_buffer_lock = threading.Lock()


def get_buffer(user_id: str, tab_id: int) -> AudioBuffer:
    """Get or create buffer for (user_id, tab_id)."""
    with _buffer_lock:
        key = (user_id, tab_id)
        if key not in _audio_buffers:
            _audio_buffers[key] = AudioBuffer(max_chunks=10)
        return _audio_buffers[key]


def clear_session_buffer(user_id: str, tab_id: int) -> None:
    """Clear buffer for a session (e.g., when tab closes)."""
    with _buffer_lock:
        key = (user_id, tab_id)
        if key in _audio_buffers:
            _audio_buffers[key].clear()


# =========================================================
# ASR ENGINE: FASTER-WHISPER
# =========================================================
_whisper_model = None
_whisper_lock = threading.Lock()


def load_whisper_model():
    """
    Lazy-load faster-whisper model on first use.
    
    INSTALLATION:
      pip install faster-whisper
    
    Supported models (in order of speed vs. quality):
      - tiny (39M) - fastest, lower quality
      - base (74M)
      - small (244M)
      - medium (769M)
      - large (3.1B) - best quality but slowest
    """
    global _whisper_model
    
    with _whisper_lock:
        if _whisper_model is not None:
            return _whisper_model
        
        try:
            from faster_whisper import WhisperModel
            
            print("[ASR] Loading Whisper 'base' model (first load may take ~30s)...")
            _whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
            print("[ASR] Whisper model loaded successfully")
            return _whisper_model
        except ImportError:
            print("[ASR] ERROR: faster-whisper not installed. Install with:")
            print("       pip install faster-whisper")
            raise
        except Exception as e:
            print(f"[ASR] ERROR loading Whisper model: {e}")
            raise


def transcribe_audio_bytes(audio_bytes: bytes) -> Optional[List[TranscriptSegment]]:
    """
    Transcribe audio bytes using faster-whisper.
    
    Returns:
        List of TranscriptSegment or None if transcription fails.
    """
    try:
        model = load_whisper_model()
        
        # Wrap bytes in BytesIO for Whisper (expects file-like object)
        audio_file = io.BytesIO(audio_bytes)
        
        print(f"[ASR] Transcribing {len(audio_bytes)} bytes...")
        
        # Transcribe with default language (auto-detect)
        segments, info = model.transcribe(
            audio_file,
            language=None,  # Auto-detect
            task="transcribe",
            temperature=0.0,  # More deterministic
            beam_size=5,
            vad_filter=True,  # Voice Activity Detection (skip silence)
        )
        
        # Convert to TranscriptSegment objects
        transcript_segments = []
        for segment in segments:
            ts = TranscriptSegment(
                text=segment.text.strip(),
                start_seconds=segment.start,
                end_seconds=segment.end,
                confidence=segment.confidence if hasattr(segment, 'confidence') else 0.9,
            )
            transcript_segments.append(ts)
            print(f"[ASR]   [{ts.start_seconds:.2f}-{ts.end_seconds:.2f}] {ts.text}")
        
        if not transcript_segments:
            print("[ASR] No speech detected in audio")
        
        return transcript_segments
    
    except Exception as e:
        print(f"[ASR] ERROR during transcription: {e}")
        return None


# =========================================================
# MAIN HANDLER: Process audio chunk
# =========================================================
PROCESS_EVERY_N_CHUNKS = 3  # Run ASR every 3 chunks (~3 seconds at 1 sec/chunk)


def process_audio_chunk(
    user_id: str,
    tab_id: int,
    seq: int,
    audio_b64: str,
    mime_type: str = "audio/webm;codecs=opus"
) -> Optional[List[TranscriptSegment]]:
    """
    Process incoming audio chunk:
      1. Decode base64 -> bytes
      2. Add to buffer for (user_id, tab_id)
      3. Every PROCESS_EVERY_N_CHUNKS: run ASR on accumulated audio
      4. Return segments or None
    
    Args:
        user_id: User identifier
        tab_id: Chrome tab ID
        seq: Sequence number of chunk
        audio_b64: Base64-encoded audio data
        mime_type: Audio MIME type
    
    Returns:
        List of TranscriptSegment if ASR was run, else None.
    """
    try:
        # Decode base64 to bytes
        audio_bytes = base64.b64decode(audio_b64)
        print(f"[ASR] Chunk {seq}: decoded {len(audio_bytes)} bytes from base64")
        
        # Add to buffer
        buffer = get_buffer(user_id, tab_id)
        buffer.add_chunk(seq, audio_bytes)
        
        # Check if we should run ASR (every N chunks)
        with buffer.lock:
            chunk_count = len(buffer.chunks)
        
        if chunk_count % PROCESS_EVERY_N_CHUNKS != 0:
            print(f"[ASR] Buffered {chunk_count} chunks (waiting for {PROCESS_EVERY_N_CHUNKS})")
            return None
        
        print(f"[ASR] Running ASR on {chunk_count} accumulated chunks...")
        
        # Get all audio bytes from buffer (WITHOUT clearing)
        audio_all = buffer.get_all_bytes()
        if not audio_all:
            print("[ASR] ERROR: No audio data in buffer")
            return None
        
        # Run transcription
        segments = transcribe_audio_bytes(audio_all)
        
        # Only clear buffer if ASR succeeded
        if segments is not None:
            buffer.clear()
            print(f"[ASR] ASR complete: {len(segments)} segments, buffer cleared")
            return segments
        else:
            # ASR failed; keep buffer for retry
            print("[ASR] ASR failed; keeping buffer for retry")
            return None
    
    except Exception as e:
        print(f"[ASR] ERROR in process_audio_chunk: {e}")
        return None
