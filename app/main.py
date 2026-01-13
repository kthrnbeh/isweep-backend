# app/main.py
"""
ISweep FastAPI backend.
Acts as the central decision engine for filtering behavior.
"""

from typing import Any
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .models import Preference, Event, DecisionResponse
from . import rules

# -------------------------------------------------
# CREATE APP (MUST BE BEFORE ANY @app.* DECORATORS)
# -------------------------------------------------
app = FastAPI(
    title="ISweep Backend",
    description="AI brain that decides when to mute, skip, or fast-forward.",
    version="0.1.0",
)

# -------------------------------------------------
# CORS
# -------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------
# HEALTH CHECK
# -------------------------------------------------
@app.get("/health")
def health_check() -> dict[str, Any]:
    return {
        "status": "ok",
        "message": "ISweep backend is alive",
    }

# -------------------------------------------------
# SAVE USER PREFERENCES
# -------------------------------------------------
@app.post("/preferences")
def set_preference(pref: Preference) -> dict[str, Any]:
    rules.save_preference(pref)
    return {
        "status": "saved",
        "preference": pref.model_dump(),
    }

# -------------------------------------------------
# EVENT DECISION ENDPOINT
# -------------------------------------------------
@app.post("/event", response_model=DecisionResponse)
def handle_event(event: Event) -> DecisionResponse:
    decision = rules.decide(event)
    return decision
