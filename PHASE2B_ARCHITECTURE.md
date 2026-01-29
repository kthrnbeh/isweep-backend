# ISweep Phase 2b: Architecture Diagram

## End-to-End ASR Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    YOUTUBE VIDEO                                │
│                (Captions OFF / ASR Enabled)                     │
└──────────────────────────────────────┬──────────────────────────┘
                                        │
                                        ▼
                    ┌───────────────────────────────────┐
                    │  Chrome Extension (offscreen.js)  │
                    │  ✓ chrome.tabCapture()            │
                    │  ✓ MediaRecorder                  │
                    │  ✓ Chunk every 1000ms             │
                    │  ✓ Encode to base64               │
                    └──────────────┬──────────────────┘
                                    │
                                    │ (seq=1)
                                    ├─────────────────────┐
                                    │ (seq=2)             │
                                    │                     │
                                    │ (seq=3) ◄─── Trigger ASR
                                    ▼
                    ┌────────────────────────────────────┐
                    │  Backend: POST /asr/stream         │
                    │  Input: AudioChunk                 │
                    │  {                                 │
                    │    user_id: "user123"              │
                    │    tab_id: 456                     │
                    │    seq: 3                          │
                    │    mime_type: "audio/webm;..."    │
                    │    audio_b64: "GkXfo59..."         │
                    │  }                                 │
                    └──────────────┬──────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI Route Handler                       │
├─────────────────────────────────────────────────────────────────┤
│  1. Validate input (user_id, tab_id, audio_b64)                │
│  2. Call asr.process_audio_chunk()                             │
│     └─ Decode base64 → audio bytes                             │
│     └─ Get buffer for (user_id, tab_id)                        │
│     └─ Add bytes to buffer                                     │
│     └─ Check: len(buffer) % 3 == 0?                           │
│        └─ NO: return { segments: [] } (buffering)              │
│        └─ YES: proceed to ASR                                  │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                  ASR Processing (asr.py)                        │
├─────────────────────────────────────────────────────────────────┤
│  1. Load Whisper model (once, lazy-loaded)                     │
│     └─ Model: "base" (74M)                                     │
│     └─ Device: CPU (can use CUDA if available)                │
│  2. Get all audio from buffer (3 chunks = ~3 seconds)          │
│  3. Run transcription:                                          │
│     transcribe(audio_file, language=None, vad_filter=True)    │
│  4. Extract segments:                                           │
│     For each segment:                                           │
│       - text: transcribed words                                │
│       - start_seconds: start time                              │
│       - end_seconds: end time                                  │
│       - confidence: confidence score (0-1)                    │
│  5. Clear buffer on success                                    │
│  6. Return segments (or empty on error)                        │
└──────────────────┬───────────────────────────────────────────┘
                   │
                   ▼
                Response: 200 OK
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
                   │
                   ▼
    ┌──────────────────────────────────────┐
    │  Extension: Process Segments         │
    │  For each segment:                   │
    │  1. Send to content-script via       │
    │     chrome.tabs.sendMessage()        │
    │  2. Inject window.__isweepIngest({   │
    │       text: segment.text,            │
    │       timestamp: segment.start_s,    │
    │       source: 'backend_asr'          │
    │     })                               │
    └──────────────────┬───────────────────┘
                       │
                       ▼
    ┌──────────────────────────────────────┐
    │  Content Script: TranscriptEngine    │
    │  (youtube-handler.js already works)  │
    │  1. Deduplicate via .source          │
    │  2. Parse for blocked_words          │
    │  3. Decide action (mute/skip)        │
    │  4. Execute on video                 │
    └──────────────────┬───────────────────┘
                       │
                       ▼
    ┌──────────────────────────────────────┐
    │  YouTube Video Action                │
    │  ✓ Auto-mute                         │
    │  ✓ Auto-skip                         │
    │  ✓ Fast-forward                      │
    └──────────────────────────────────────┘
```

## Session Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│  User opens YouTube + enables ASR toggle                    │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
    ┌────────────────────────────────────┐
    │  offscreen.js: START_ASR message   │
    │  1. chrome.tabCapture.capture()    │
    │  2. Create MediaRecorder           │
    │  3. Start chunking loop            │
    │  4. Track activeAsrTabId           │
    └────────────┬───────────────────────┘
                 │
        ┌────────┴────────┐
        ▼                 ▼
    Chunks POST'd to /asr/stream
    User watches video...
    Transcription in real-time
        │                 │
        └────────┬────────┘
                 │
    ┌───────────┴──────────────┐
    │  User disables ASR OR    │
    │  Closes tab              │
    └───────────┬──────────────┘
                 │
                 ▼
    ┌────────────────────────────────────┐
    │  background.js: STOP_ASR message   │
    │  1. offscreen.js stops chunking    │
    │  2. Close media stream              │
    │  3. Clear activeAsrTabId           │
    │  4. Cleanup buffer (optional)      │
    └────────────────────────────────────┘
```

## Memory Layout

```
┌──────────────────────────────────────────────────────────────────┐
│                    Python Process Memory                         │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─ Global Whisper Model (ONCE, shared) ──────────────────┐    │
│  │  WhisperModel("base", device="cpu", compute_type="int8")   │
│  │  Size: ~500 MB                                         │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─ Buffer Store: Dict[Tuple, AudioBuffer] ──────────────┐    │
│  │  Key: (user_id, tab_id)                               │    │
│  │  ┌─ (user123, 456)                                    │    │
│  │  │   AudioBuffer:                                     │    │
│  │  │   chunks: [(seq=1, bytes), (seq=2, bytes), ...]    │    │
│  │  │   Size: ~10 chunks × 1-2 MB = ~20 MB max          │    │
│  │  │                                                    │    │
│  │  ├─ (user123, 789)                                    │    │
│  │  │   AudioBuffer: ...                                 │    │
│  │  │                                                    │    │
│  │  └─ (user456, 123)                                    │    │
│  │      AudioBuffer: ...                                 │    │
│  │                                                       │    │
│  │  Total: 100 concurrent users × 20 MB = ~2 GB         │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─ Locks (Thread-safe) ────────────────────────────────┐      │
│  │  _buffer_lock: protects _audio_buffers dict          │      │
│  │  buffer.lock: protects individual buffer.chunks      │      │
│  │  _whisper_lock: protects model loading               │      │
│  └──────────────────────────────────────────────────────┘      │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

## Request Timeline (3-chunk example)

```
Time    Event
────────────────────────────────────────────────────────
t=0s    YouTube video playing, captions OFF, ASR enabled
        Tab ID 456, User "user123"

t=1s    Chunk 1 sent
        POST /asr/stream: seq=1, audio_b64="..."
        Response: { segments: [] }  (buffering)
        Buffer: [chunk1]

t=2s    Chunk 2 sent
        POST /asr/stream: seq=2, audio_b64="..."
        Response: { segments: [] }  (buffering)
        Buffer: [chunk1, chunk2]

t=3s    Chunk 3 sent
        POST /asr/stream: seq=3, audio_b64="..."
        ✓ Trigger ASR (3 % PROCESS_EVERY_N_CHUNKS == 0)
        
        [ASR] Running ASR on 3 accumulated chunks...
        [ASR] Transcribing ~6KB bytes...
        [ASR] [0.50-1.20] Hello world
        [ASR] [1.50-2.80] This is a test
        Response: { segments: [seg1, seg2] }
        Buffer cleared: []

t=3.5s  Extension receives segments
        → Send to content-script (2 messages)
        → __isweepTranscriptIngest called x2

t=3.6s  TranscriptEngine processes:
        - "Hello world" vs blocked_words
        - "This is a test" vs blocked_words
        - Decision: MUTE (if match)

t=3.7s  YouTube video muted (if action=mute)
        OR skipped (if action=skip)

t=4s    Chunk 4 sent (continue...)
        Buffer: [chunk4]
```

## Error Scenarios & Recovery

```
Scenario 1: Invalid Audio Data
  Input: audio_b64 = "invalid!@#$"
  ✓ base64.b64decode() raises exception
  ✓ Caught in try-except
  ✓ Return: { segments: [] }
  ✓ Log: [ASR] ERROR: Invalid base64 data
  ✓ No server crash

Scenario 2: Out of Memory
  Setup: Running 1000 concurrent users
  ✓ Memory grows: 1000 × 20 MB = 20 GB
  ✗ Eventually: MemoryError or OOM kill
  Mitigation:
    - Reduce max_chunks: 10 → 5 (-50% memory)
    - Use "tiny" model: 500 MB → 100 MB
    - Implement LRU cache with TTL
    - Horizontal scaling (multiple servers)

Scenario 3: Slow Transcription
  Setup: Large model on CPU
  Problem: ASR takes 10 seconds, user expects <2 seconds
  Solution options:
    - Reduce PROCESS_EVERY_N_CHUNKS: 3 → 1 (more frequent, smaller batches)
    - Use GPU: device="cuda" (3x-10x speedup)
    - Use smaller model: "tiny" (faster but lower quality)

Scenario 4: Extension Disables ASR
  User toggles ASR OFF
  ✓ background.js: stopAsr()
  ✓ Send STOP_ASR to offscreen
  ✓ offscreen.js: closes stream, stops chunking
  ✓ Buffer remains (for recovery if re-enabled)
  ✓ Session cleanup optional
```

## Comparison: Captions vs. ASR

```
Dimension        Captions (Phase 1)    ASR (Phase 2b)
─────────────────────────────────────────────────────
Latency          0-500ms (DOM)         3-8s (processing)
Availability     ✓ When enabled        ✓ YouTube + others
Accuracy         ✓ 99%+ (human)        ✓ 80-95% (Whisper)
Cost             Free                  CPU usage (~2-5s per 3s audio)
Fallback         ✗ None if disabled    ✓ ASR if captions off
Audio needed     ✗ No (text only)      ✓ Yes (tab capture)
Privacy          ✓ Local (YouTube)     ✓ Local (Whisper)

ISweep Strategy:
  Primary:   Captions (fast, accurate, YouTube-native)
  Fallback:  ASR (when captions unavailable)
  Combined:  Use both, merge results, pick best match
```

---

**Diagram Version:** Phase 2b (2026-01-28)
**Accuracy:** Matches implementation in asr.py + main.py
