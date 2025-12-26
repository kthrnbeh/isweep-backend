# app/main.py
# -------------------------------------------------
# This file creates the FastAPI backend server for ISweep.
#
# 🧠 Think of this as the "AI brain" that reacts to what the
#    video player is seeing/hearing.
#
# The frontend (browser extension, YouTube overlay, TV app,
# desktop app, or the Help demo page) sends information HERE.
#
# The backend then decides:
#   - Should we mute the video?
#   - Should we skip ahead?
#   - Should we fast-forward?
#   - Should we do nothing?
#
# ⚡ The frontend NEVER decides filtering behavior itself.
#    It only follows the instructions returned from this backend.
#
# This keeps the logic centralized, predictable, and easy to update.
# -------------------------------------------------

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# We import the Pydantic data models used to validate incoming JSON.
# These enforce correct data structure and types.
#
# Preference       → describes what the user WANTS filtered
# Event            → describes what the frontend DETECTS
# DecisionResponse → describes what the backend DECIDES
#
# These are the shared contract between backend and frontend.
from .models import Preference, Event, DecisionResponse

# Import the decision engine.
# rules.py contains:
#   - save_preference()  → store user settings
#   - decide()           → read an Event, output a filtering decision
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
# CORS Middleware — allows browser-based frontends to talk to backend
# -------------------------------------------------
# WHY THIS IS CRITICAL:
#   - A Chrome extension runs under a URL like:
#         chrome-extension://abcd1234
#
#   - Your local HTML demo runs under:
#         http://127.0.0.1:5500
#
#   - Your backend runs at:
#         http://127.0.0.1:8000
#
# Browsers *block* communication between different origins unless CORS allows it.
#
# This middleware tells the browser:
#     "Yes, the ISweep backend ALLOWS requests from any page for now."
#
# Later, you can lock this down to only your extension or website.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # ALL domains allowed during development
    allow_credentials=True,
    allow_methods=["*"],   # GET, POST, PUT, DELETE all allowed
    allow_headers=["*"],   # Allow any headers
)


# -------------------------------------------------
# HEALTH CHECK ENDPOINT
# -------------------------------------------------
# Why this matters:
#   - Your extension can check if the backend is online.
#   - Your Help page can verify the system is running.
#   - You can test if your backend server booted successfully.
@app.get("/health")
def health_check():
    """
    Simple endpoint to test backend connectivity.

    Helpful for:
      - debugging
      - ensuring server is live before sending events
      - verifying that your browser extension found the backend
    """
    return {"status": "ok", "message": "ISweep backend is alive"}


# -------------------------------------------------
# USER PREFERENCE ENDPOINT
# -------------------------------------------------
# This receives user settings from the Settings page.
#
# Examples of preferences:
#   - category: "language" → action: "mute" for 4 seconds
#   - category: "sexual"   → action: "skip" for 30 seconds
#   - category: "violence" → action: "fast_forward"
#
# The frontend POSTS a Preference object here to save rules.
@app.post("/preferences")
def set_preference(pref: Preference):
    """
    Stores or updates user filtering rules.

    FRONTEND CALLS THIS WHEN:
      - A user checks/unchecks a filter category in Settings
      - A user changes an action (mute/skip/FF)
      - A user updates blocked words
      - The app initializes default preferences on first run

    HOW THIS WORKS IN THE WHOLE PROGRAM:

      Settings Page → JS → POST /preferences → rules.save_preference()
      Then the next time /event is triggered:
         rules.decide() uses these new preferences.

    That means:
    - If the user disables profanity filtering, the backend will stop muting.
    - If they increase skip duration, the backend will skip longer.
    """
    rules.save_preference(pref)
    return {"status": "saved", "preference": pref}


# -------------------------------------------------
# EVENT DECISION ENDPOINT
# -------------------------------------------------
# This is the MOST IMPORTANT endpoint.
#
# 🎥 It receives REAL-TIME content from the frontend:
#      - subtitle text
#      - speech-to-text results
#      - timestamps
#      - AI detection results
#
# After reading the Event, ISweep decides:
#      "Do nothing"
#      "Mute"
#      "Skip ahead"
#      "Fast forward"
#
# Then the frontend video player performs the action.
@app.post("/event", response_model=DecisionResponse)
def handle_event(event: Event):
    """
    The frontend sends an Event object whenever it detects something.

    Event examples:
      - Subtitle: "oh my god why did you do that?"
      - Content model: {type: "violence", confidence: 0.88}
      - User override: manual skip pressed

    FLOW OF THIS FUNCTION:

      1. Input JSON gets converted into an Event model.
      2. The backend passes it to rules.decide(event).
      3. rules.decide():
            • Looks up matching user preference
            • Detects blocked words
            • Considers content_type and confidence
            • Builds a DecisionResponse
      4. The decision is returned to the frontend.

    FRONTEND THEN:
      - If action=“mute” → mutes video for X seconds
      - If action=“skip” → jumps ahead
      - If action=“fast_forward” → temporarily speeds playback
      - If action=“none” → nothing happens

    This is the full AI filtering loop.
    """
    decision = rules.decide(event)
    return decision


# -------------------------------------------------
# End of app/main.py
# -------------------------------------------------
