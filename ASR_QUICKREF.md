# Phase 2b: Quick Reference

## 🚀 Start Here

### 1. Install Whisper (one-time)
```bash
pip install faster-whisper
```

### 2. Start Backend
```bash
cd c:\ISweep_wireframe\isweep-backend
python -m app
```

Backend will:
- ✓ Initialize Whisper model on first request
- ✓ Listen on http://localhost:8001
- ✓ Serve API docs at /docs

### 3. Test Endpoint
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

Expected response:
```json
{
  "segments": []
}
```

## 📋 API Reference

### POST /asr/stream

**Input:**
```json
{
  "user_id": "user123",
  "tab_id": 456,
  "seq": 1,
  "mime_type": "audio/webm;codecs=opus",
  "audio_b64": "GkXfo59UJ+v/3v/7V1V="
}
```

**Output (segments found):**
```json
{
  "segments": [
    {
      "text": "Hello world",
      "start_seconds": 0.5,
      "end_seconds": 1.2,
      "confidence": 0.92
    }
  ]
}
```

**Output (buffering):**
```json
{
  "segments": []
}
```

**Status Codes:**
- `200`: OK (with or without segments)
- `400`: Invalid input (missing user_id, tab_id, etc.)
- `500`: Server error (graceful, returns empty segments)

## ⚙️ Configuration

### Buffer Size
**File:** `app/asr.py` line 51
```python
AudioBuffer(max_chunks=10)  # Default: keep last 10 chunks (~10 seconds)
```

### Process Frequency
**File:** `app/asr.py` line 85
```python
PROCESS_EVERY_N_CHUNKS = 3  # Run ASR every 3 chunks (~3 seconds)
```

### Whisper Model
**File:** `app/asr.py` line 104
```python
WhisperModel("base", device="cpu", compute_type="int8")
```

**Options:**
- `"tiny"`: 39M (fastest, lower quality)
- `"base"`: 74M (default, good balance)
- `"small"`: 244M (better quality, slower)
- `"medium"`: 769M (excellent quality, very slow)

### Language
**File:** `app/asr.py` line 145
```python
segments, info = model.transcribe(audio_file, language=None)  # Auto-detect
```

Force language:
```python
segments, info = model.transcribe(audio_file, language="en")  # Force English
```

## 🔍 Debugging

### Monitor Logs
```bash
# Real-time ASR logs
python -m app 2>&1 | grep "\[ASR\]"
```

### Example Log Output
```
[ASR] /asr/stream: user=user123 tab=456 seq=1
[ASR] Chunk 1: decoded 2048 bytes from base64
[ASR] Buffered 1 chunks (waiting for 3)
...
[ASR] Chunk 3: decoded 2031 bytes from base64
[ASR] Running ASR on 3 accumulated chunks...
[ASR] Transcribing 6094 bytes...
[ASR]   [0.50-1.20] Hello world
[ASR]   [1.50-2.80] This is a test
[ASR] ASR complete: 2 segments, buffer cleared
```

### Common Issues

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: faster_whisper` | `pip install faster-whisper` |
| Model download stuck | Check disk space, run in background, wait 30-60s |
| Transcription garbage | Force language: `language="en"` in asr.py line 145 |
| Slow performance (>10s) | Use smaller model or GPU (`device="cuda"`) |
| High memory usage | Reduce `max_chunks` from 10 to 5 |

## 🧪 Test Scenarios

### Scenario 1: Dummy Audio
```bash
curl -X POST http://localhost:8001/asr/stream \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","tab_id":1,"seq":1,"mime_type":"audio/webm;codecs=opus","audio_b64":"GkXfo59UJ+v/3v/7V1V="}'
```
Expected: `{ "segments": [] }` (no crash)

### Scenario 2: Real Audio from Extension
1. Enable ASR in extension
2. Play YouTube video (captions OFF, volume ON)
3. Check Chrome DevTools: `[ISweep-ASR]` logs
4. Backend should show transcription every 3 chunks

### Scenario 3: Multiple Users
```bash
# User 1, Tab 1, Chunk 1
curl ... -d '{"user_id":"user1","tab_id":101,"seq":1,...}'

# User 2, Tab 1, Chunk 1 (different user!)
curl ... -d '{"user_id":"user2","tab_id":101,"seq":1,...}'

# Both should have separate buffers
```

### Scenario 4: Error Handling
```bash
# Missing user_id
curl -X POST http://localhost:8001/asr/stream \
  -H "Content-Type: application/json" \
  -d '{"tab_id":1,"seq":1,"mime_type":"audio/webm","audio_b64":"GkXfo59..."}'
```
Expected: `400 user_id required`

## 📚 File Structure

```
isweep-backend/
├── app/
│   ├── __init__.py
│   ├── __main__.py
│   ├── main.py              ← POST /asr/stream route
│   ├── models.py            ← AudioChunk, TranscriptSegment
│   ├── asr.py               ← Audio buffering + Whisper (NEW)
│   ├── rules.py
│   └── database.py
├── requirements.txt
├── ASR_SETUP.md             ← Full setup guide
├── PHASE2B_SUMMARY.md       ← Implementation summary
└── PHASE2B_ARCHITECTURE.md  ← Diagrams + architecture
```

## 🎯 Next Steps

1. **Install:** `pip install faster-whisper`
2. **Start:** `python -m app`
3. **Test:** Send dummy chunk or use extension
4. **Monitor:** `grep "\[ASR\]"` in logs
5. **Integrate:** Update offscreen.js to POST chunks
6. **End-to-end test:** Enable ASR on YouTube + verify filtering

## 📊 Expected Performance

| Metric | Value |
|--------|-------|
| Latency per POST | 10-50ms |
| ASR latency (3 chunks) | 2-5s |
| Memory per user | 25-30 MB |
| Max concurrent users | 10-50 (CPU-dependent) |

## ✨ Highlights

- ✅ **No crashes:** Errors → empty segments
- ✅ **Concurrent:** Thread-safe buffers per (user, tab)
- ✅ **Configurable:** Model size, buffer size, chunk frequency
- ✅ **Debuggable:** `[ASR]` prefix on all logs
- ✅ **Production-ready:** Type hints, docstrings, error handling

## 🎓 More Info

- Full setup: See `ASR_SETUP.md`
- Architecture: See `PHASE2B_ARCHITECTURE.md`
- Implementation summary: See `PHASE2B_SUMMARY.md`
- Code: `app/asr.py` (buffering) + `app/main.py` (route)

---

**Last Updated:** 2026-01-28
**Phase:** 2b (Backend ASR streaming)
**Status:** ✅ Ready to test
