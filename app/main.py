# app/main.py
# -------------------------------------------------
# This file creates the FastAPI backend server for ISweep.
# The backend is the “AI brain” of the remote-control system.
#
# The frontend (browser extension, website demo, mobile app, TV app)
# sends data TO this server:
#   - user settings (/preferences)
#   - detected text, subtitles, or scene events (/event)
#
# And this server replies WITH:
#   - decisions: mute, skip, fast-forward, or none
#
# The frontend then applies these actions to the video player.
# -------------------------------------------------

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import your Pydantic models
# Preference  = what the user wants (mute profanity, skip sexual content, etc.)
# Event       = what the AI/player detected (subtitle line, timestamp, etc.)
# DecisionResponse = what action ISweep decides to take on the video
from .models import Preference, Event, DecisionResponse

# The business logic lives in rules.py:
#   - save_preference() stores user preferences in memory
#   - decide() receives an Event and decides if action is needed
from . import rules


# -------------------------------------------------
# Create the FastAPI application object
# -------------------------------------------------
app = FastAPI(
    title="ISweep Backend",
    description="AI remote brain that decides when to mute/skip/fast-forward.",
    version="0.1.0",
)

# -------------------------------------------------
# CORS Middleware
# -------------------------------------------------
# CORS = Cross-Origin Resource Sharing.
# When your website or Chrome extension runs on:
#   http://localhost:5500   (or)
#   chrome-extension://...
#
# and it tries to call this backend at:
#   http://127.0.0.1:8000
#
# the browser normally blocks this (security rule).
#
# This middleware allows your frontends to talk to this server.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow ANY origin during development
                          # (later you may restrict to only your domain/extension)
    allow_credentials=True,
    allow_methods=["*"],  # allow all HTTP verbs: GET, POST, PUT, etc.
    allow_headers=["*"],  # allow all header types
)


# -------------------------------------------------
# HEALTH CHECK ENDPOINT
# -------------------------------------------------
@app.get("/health")
def health_check():
    """
    Simple endpoint to see if the server is running.
    - Chrome extension frontend calls this at startup
    - Help page demo can call this to verify backend link
    - Useful for debugging

    Returns:
      {"status": "ok", "message": "ISweep backend is alive"}
    """
    return {"status": "ok", "message": "ISweep backend is alive"}


# -------------------------------------------------
# USER PREFERENCE ENDPOINT
# -------------------------------------------------
@app.post("/preferences")
def set_preference(pref: Preference):
    """
    This endpoint receives user preferences.

    The frontend sends things like:
    - The categories the user wants filtered (profanity, sexual, violence)
    - What action to apply (mute, skip, fast-forward)
    - How long (duration_seconds)
    - Whether the preference is enabled
    - A list of blocked_words (for text-based filtering)

    The Preference model (in models.py) validates the data.
    Then we forward the preference to rules.save_preference()
    which stores it in an in-memory dictionary:
        RULES[user_id][content_type] = Preference()

    Example JSON body sent from frontend:
    {
      "user_id": "user123",
      "content_type": "language",
      "action": "mute",
      "duration_seconds": 5,
      "enabled": true,
      "blocked_words": ["badword", "dummy"]
    }

    This endpoint is called:
      - When the user changes Settings on the frontend
      - When the app loads and syncs default preferences
    """
    rules.save_preference(pref)
    return {"status": "saved", "preference": pref}


# -------------------------------------------------
# EVENT DECISION ENDPOINT
# -------------------------------------------------
@app.post("/event", response_model=DecisionResponse)
def handle_event(event: Event):
    """
    This endpoint receives REAL-TIME events from the frontend.

    The frontend (your Chrome extension or help-demo page) will send:
    - "user_id"            → identify whose rules to apply
    - "timestamp"          → where the video currently is
    - "source"             → browser / TV / extension
    - "text"               → subtitle line or detected transcript
    - "content_type"       → sometimes pre-labeled (future)
    - "confidence"         → probability score (future)
    - "manual_override"    → not used yet

    FASTAPI flows:
    1. The JSON body is validated against the Event model.
    2. The event is passed to rules.decide(event)
    3. rules.decide():
         - Looks up user preferences
         - Checks event.text for blocked words
         - Applies rules to decide action:
             mute / skip / fast_forward / none
         - Returns DecisionResponse

    That DecisionResponse is forwarded straight back to the frontend.

    Example JSON sent from frontend:
    {
      "user_id": "user123",
      "timestamp": 120.5,
      "source": "browser",
      "text": "oh my god why did you do that",
      "content_type": null,
      "confidence": null
    }

    Example returned:
    {
      "action": "mute",
      "duration_seconds": 4,
      "show_icon": true,
      "reason": "Blocked word: oh my god"
    }

    The frontend then executes the action on the video.
    (Your JS mutes, fast-forwards, or skips.)
    """
    decision = rules.decide(event)
    return decision
# End of app/main.py