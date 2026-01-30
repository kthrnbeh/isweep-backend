# ISweep Backend

Decision engine API for content filtering. Decides when to mute, skip, or fast-forward based on user preferences.

## Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Set up environment (optional)
```bash
cp .env.example .env
# Edit .env if needed
```

### 3. Run the server
```bash
python -m app --host 127.0.0.1 --port 8001 --no-reload
```

Server starts at `http://127.0.0.1:8001`

**API Documentation:**
- Interactive docs: http://127.0.0.1:8001/docs
- ReDoc: http://127.0.0.1:8001/redoc

---

## Windows (PowerShell) Baby Steps

Run these exact commands in PowerShell from the backend folder:

```powershell
cd c:\ISweep_wireframe\isweep-backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

Then open this in your browser to verify:

```
http://127.0.0.1:8001/health
```

### 4. Run tests
```bash
pytest
# With coverage:
pytest --cov=app tests/
```

---

## Architecture

### Core Components

- **main.py** — FastAPI app, endpoints, dependency injection
- **models.py** — Pydantic schemas (Preference, Event, DecisionResponse)
- **rules.py** — Decision logic and preference management
- **database.py** — SQLAlchemy ORM setup and models
- **__main__.py** — CLI entry point

### Database

Uses **SQLite** for persistence. Tables:
- `preferences` — Stores user filtering preferences by category

Located at `isweep.db` (configurable via `ISWEEP_DB_PATH`).

---

## API Endpoints

### Health Check
```
GET /health
```
Returns server status.

### Save/Update Preference
```
POST /preferences
Content-Type: application/json

{
  "user_id": "user123",
  "category": "language",
  "enabled": true,
  "action": "mute",
  "duration_seconds": 4,
  "blocked_words": ["bad1", "bad2"]
}
```

### Get All User Preferences
```
GET /preferences/{user_id}
```
Returns all preferences for a user, with defaults for unconfigured categories.

### Process Event (Decision)
```
POST /event
Content-Type: application/json

{
  "user_id": "user123",
  "text": "Some content to filter",
  "content_type": "language",
  "confidence": 0.92
}
```

**Response:**
```json
{
  "action": "mute",
  "duration_seconds": 4,
  "reason": "Blocked word match: 'bad1'",
  "matched_category": "language"
}
```

---

## Preferences & Actions

### Categories
- `language` — Profanity, offensive speech
- `sexual` — Sexual content
- `violence` — Violent content

### Actions
- `none` — No action (default)
- `mute` — Mute/silence for duration
- `skip` — Skip to next segment
- `fast_forward` — Speed up for duration

### Defaults
```
language:  mute for 4s
sexual:    skip for 30s
violence:  fast-forward for 10s
```

---

## Configuration

Via `.env` file:

| Variable | Default | Purpose |
|----------|---------|---------|
| `ISWEEP_DB_PATH` | `isweep.db` | SQLite database path |
| `ISWEEP_DEBUG` | `false` | Enable SQL query logging |

---

## Development

### Add a new feature
1. Update models in `models.py`
2. Add logic to `rules.py`
3. Add endpoint in `main.py`
4. Write tests in `tests/test_rules.py`
5. Run `pytest` to verify

### Database Migrations
For now, schema is auto-created. To reset:
```bash
rm isweep.db
# Restart server to recreate tables
```

---

## Testing

```bash
# All tests
pytest

# Specific test file
pytest tests/test_rules.py

# With verbose output
pytest -v

# Coverage report
pytest --cov=app --cov-report=html tests/
```

---

## Deployment

### Production
1. Set `ISWEEP_DEBUG=false`
2. Run with Gunicorn:
   ```bash
   gunicorn -w 4 -b 0.0.0.0:8000 app.main:app
   ```

### Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "-m", "app", "--host", "0.0.0.0"]
```

---

## Future Enhancements

- [ ] User authentication / API keys
- [ ] Rate limiting
- [ ] Analytics (decision history)
- [ ] ML model for confidence scoring
- [ ] WebSocket for real-time streaming
- [ ] Database migrations tool
