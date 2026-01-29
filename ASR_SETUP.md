# Phase 2b: ASR Backend Setup

## Quick Start

### 1. Install faster-whisper

```bash
pip install faster-whisper
```

**First run will download the model (~1.4 GB for "base" model) automatically.**

### 2. Verify Installation

```bash
python -c "from faster_whisper import WhisperModel; print('✓ faster-whisper OK')"
```

### 3. Start Backend

```bash
python -m app
# or
uvicorn app.main:app --reload --port 8001
```

### 4. Test Endpoint

**Interactive API docs:** http://localhost:8001/docs

## Architecture Overview

### Components

| File | Purpose |
|------|---------|
| `app/models.py` | `AudioChunk`, `TranscriptSegment`, `ASRStreamResponse` Pydantic models |
| `app/asr.py` | Audio buffering, Whisper ASR processing, session management |
| `app/main.py` | FastAPI app, `/asr/stream` POST endpoint |

### Flow

```
Chrome Extension (offscreen.js)
    ↓
POST /asr/stream { user_id, tab_id, seq, mime_type, audio_b64 }
    ↓
app/main.py (route handler)
    ↓
app/asr.py:
  1. Decode base64 → audio bytes
  2. Buffer in memory: (user_id, tab_id) → AudioBuffer
  3. Every 3 chunks (~3 seconds):
     - Get all buffered audio
     - Run Whisper ASR
     - Return transcribed segments
     - Clear buffer
    ↓
Response: { segments: [ { text, start_seconds, end_seconds, confidence } ] }
    ↓
Extension: Route through __isweepTranscriptIngest with source: 'backend_asr'
```

## API Endpoint

### POST /asr/stream

**Request:**
```json
{
  "user_id": "user123",
  "tab_id": 456,
  "seq": 1,
  "mime_type": "audio/webm;codecs=opus",
  "audio_b64": "GkXfo59UJ+v/3v/7V1V..."
}
```

**Response (segments found):**
```json
{
  "segments": [
    {
      "text": "Hello world",
      "start_seconds": 0.5,
      "end_seconds": 1.2,
      "confidence": 0.92
    },
    {
      "text": "This is a test",
      "start_seconds": 1.5,
      "end_seconds": 2.8,
      "confidence": 0.88
    }
  ]
}
```

**Response (still buffering):**
```json
{
  "segments": []
}
```

**Error (returns empty segments, does NOT crash):**
```json
{
  "segments": []
}
```

## Configuration

### Buffering Strategy

**File:** `app/asr.py`, line ~35

```python
PROCESS_EVERY_N_CHUNKS = 3  # Run ASR every 3 chunks (~3 seconds)
```

Adjust based on latency requirements:
- `1`: Process every chunk (low latency, high CPU)
- `3`: Process every 3 chunks (~3 seconds) **[DEFAULT]**
- `5`: Process every 5 chunks (~5 seconds, better batch efficiency)

### Buffer Size

**File:** `app/asr.py`, line ~51

```python
AudioBuffer(max_chunks=10)  # Keep up to 10 chunks in memory
```

Prevents unbounded memory growth. At 1 chunk/sec, 10 chunks = ~10 seconds of audio.

### Whisper Model

**File:** `app/asr.py`, line ~104

```python
_whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
```

**Available models:**

| Model | Size | Speed | Quality |
|-------|------|-------|---------|
| `tiny` | 39M | ⚡ Fastest | Lower |
| `base` | 74M | ⚡ Fast | ⭐ Good |
| `small` | 244M | 🔷 Medium | Better |
| `medium` | 769M | 🐢 Slow | Excellent |
| `large` | 3.1B | 🐢 Very Slow | Best |

**For production:** Use `small` (244M) for better accuracy with acceptable latency.

```python
# Change to:
_whisper_model = WhisperModel("small", device="cpu", compute_type="int8")
```

**With GPU (if available):**
```python
_whisper_model = WhisperModel("base", device="cuda", compute_type="float16")
```

Requires: `pip install torch[cuda]` (large download, NVIDIA GPU required)

## Production Considerations

### 1. Error Handling

All transcription errors return `{ "segments": [] }` without crashing the server.
- Invalid audio data
- Out of memory
- Model load failures

Check server logs for debugging:
```
[ASR] ERROR: ...
```

### 2. Concurrency

`asr.py` uses thread-safe locking for buffer access:
- Multiple users: separate buffers
- Same user, multiple tabs: separate buffers
- High concurrency: thread pool managed by FastAPI/Uvicorn

### 3. Memory Management

**Per-user-per-tab memory:**
- Max 10 chunks @ ~1-2 MB each = ~20 MB worst case
- With 100 concurrent users: ~2 GB
- Consider reducing `max_chunks` or buffer pruning if needed

**Model memory:**
- "base" model: ~500 MB in memory
- Global: loaded once, shared by all requests

### 4. Logging

Enable debug output:
```bash
# Already enabled by default
tail -f backend.log | grep "\[ASR\]"
```

Disable by redirecting stdout (production):
```bash
python -m app 2>/dev/null
```

## Testing

### 1. Manual Test (No Audio)

```bash
curl -X POST http://localhost:8001/asr/stream \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "tab_id": 123,
    "seq": 1,
    "mime_type": "audio/webm;codecs=opus",
    "audio_b64": "GkXfo59UJ+v/3v/7V1V="
  }'
```

Expected: `{ "segments": [] }` (invalid audio, but no crash)

### 2. Integration with Extension

1. Start backend: `python -m app`
2. Open YouTube video with captions OFF
3. Enable ASR toggle in extension popup
4. Open DevTools → Console → filter `[ISweep-ASR]`
5. You should see chunks being POSTed to `http://localhost:8001/asr/stream`
6. After 3 chunks, transcription should appear

### 3. Check Transcription Logs

```bash
# Filter ASR logs in real-time
python -m app 2>&1 | grep "\[ASR\]"
```

Example output:
```
[ASR] Chunk 1: decoded 2048 bytes from base64
[ASR] Buffered 1 chunks (waiting for 3)
[ASR] Chunk 2: decoded 2015 bytes from base64
[ASR] Buffered 2 chunks (waiting for 3)
[ASR] Chunk 3: decoded 2031 bytes from base64
[ASR] Running ASR on 3 accumulated chunks...
[ASR] Transcribing 6094 bytes...
[ASR]   [0.50-1.20] Hello world
[ASR]   [1.50-2.80] This is a test
[ASR] ASR complete: 2 segments, buffer cleared
```

## Troubleshooting

### Issue: "faster-whisper not installed"

**Solution:**
```bash
pip install faster-whisper
```

**Verify:**
```bash
python -c "from faster_whisper import WhisperModel; print('OK')"
```

### Issue: Model download stuck / slow

**Expected:** First run takes 30-60 seconds (downloading ~1.4 GB model)

**Check progress:**
```bash
# In another terminal
du -sh ~/.cache/huggingface/  # or your HF_HOME directory
```

**Speed up by pre-downloading:**
```bash
python -c "
from faster_whisper import WhisperModel
model = WhisperModel('base')
print('Model loaded successfully')
"
```

### Issue: High CPU / Slow transcription

**Causes:**
- CPU-only inference (vs GPU)
- Large model (use "tiny" or "base")
- System under load

**Solutions:**
- Use GPU: `device="cuda"` (requires NVIDIA + torch[cuda])
- Use smaller model: "tiny" (39M)
- Reduce `PROCESS_EVERY_N_CHUNKS` to process less audio per run
- Increase buffer pruning

### Issue: Out of memory

**Check memory usage:**
```bash
ps aux | grep python  # Look at VSZ (virtual) and RSS (resident)
```

**Solutions:**
1. Reduce `max_chunks` from 10 to 5
2. Use smaller model: "tiny"
3. Add buffer clearance on timeout (future enhancement)

### Issue: Transcription garbage / wrong language

**Cause:** Whisper auto-detecting wrong language

**Solution (force language):** Edit `app/asr.py` line ~145

```python
# Change from:
segments, info = model.transcribe(audio_file, language=None)

# To:
segments, info = model.transcribe(audio_file, language="en")  # Force English
```

Languages: `"en"`, `"es"`, `"fr"`, `"de"`, `"ja"`, etc.

## Next Steps

1. ✅ Phase 2b complete: `/asr/stream` endpoint ready
2. 🔄 Phase 2c (Future): Integrate ASR results into filtering pipeline
3. 🔄 Phase 3: Multi-language support, confidence filtering, cache optimization

## References

- **faster-whisper docs:** https://github.com/SYSTRAN/faster-whisper
- **Whisper paper:** https://arxiv.org/abs/2212.04356
- **ISweep Backend:** `isweep-backend/README.md`
- **Extension ASR:** `isweep-chrome-extension/offscreen.js`
