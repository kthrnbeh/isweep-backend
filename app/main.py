# app/main.py
"""
ISweep FastAPI backend.
Acts as the central decision engine for filtering behavior.
"""

from typing import Any
from fastapi import FastAPI, Depends, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .models import Preference, Event, DecisionResponse, AudioChunk, ASRStreamResponse
from . import rules, asr
from .database import init_db, get_db

# -------------------------------------------------
# CREATE APP (MUST BE BEFORE ANY @app.* DECORATORS)
# -------------------------------------------------
app = FastAPI(
    title="ISweep Backend",
    description="AI brain that decides when to mute, skip, or fast-forward.",
    version="0.1.0",
)


# -------------------------------------------------
# STARTUP EVENT
# -------------------------------------------------
@app.on_event("startup")
def startup_event():
    """Initialize database on startup."""
    init_db()


# -------------------------------------------------
# CORS
# -------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)


# -------------------------------------------------
# ROOT REDIRECT + HEALTH CHECK
# -------------------------------------------------
@app.get("/")
def root() -> dict[str, Any]:
    """Root endpoint - redirects to docs or returns status."""
    return {
        "status": "running",
        "service": "ISweep Backend",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health"
    }


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
def set_preference(pref: Preference, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Save a preference for a user."""
    try:
        if not pref.user_id.strip():
            raise HTTPException(status_code=400, detail="user_id cannot be empty")
        if not pref.category.strip():
            raise HTTPException(status_code=400, detail="category cannot be empty")
        
        rules.save_preference(db, pref)
        return {
            "status": "saved",
            "preference": pref.model_dump(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save preference: {str(e)}")


@app.post("/preferences/bulk")
def set_bulk_preferences(bulk: dict = Body(...), db: Session = Depends(get_db)) -> dict[str, Any]:
    """Save all preferences for a user in one request."""
    try:
        # Log the raw request for debugging
        import json
        print(f"[DEBUG] Received bulk request: {json.dumps(bulk, indent=2)}")
        
        # Extract user_id and preferences from request
        user_id = bulk.get('user_id', '').strip() if isinstance(bulk, dict) else ''
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id cannot be empty")
        
        preferences = bulk.get('preferences', {}) if isinstance(bulk, dict) else {}
        if not preferences:
            raise HTTPException(status_code=400, detail="preferences cannot be empty")
        
        print(f"[DEBUG] Processing {len(preferences)} categories for user: {user_id}")
        rules.save_bulk_preferences(db, user_id, preferences)
        return {
            "status": "saved",
            "user_id": user_id,
            "categories_saved": list(preferences.keys()),
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to save bulk preferences: {str(e)}")


@app.get("/preferences/{user_id}")
def get_all_preferences(user_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Get all preferences for a user."""
    try:
        if not user_id.strip():
            raise HTTPException(status_code=400, detail="user_id cannot be empty")
        
        prefs = rules.get_all_preferences(db, user_id)
        return {
            "user_id": user_id,
            "preferences": {cat: p.model_dump() for cat, p in prefs.items()},
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch preferences: {str(e)}")


# -------------------------------------------------
# EVENT DECISION ENDPOINT
# -------------------------------------------------
@app.post("/event", response_model=DecisionResponse)
def handle_event(event: Event, db: Session = Depends(get_db)) -> DecisionResponse:
    """Process an event and return a decision."""
    try:
        if not event.user_id.strip():
            raise HTTPException(status_code=400, detail="user_id cannot be empty")
        
        decision = rules.decide(db, event)
        return decision
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Decision failed: {str(e)}")
