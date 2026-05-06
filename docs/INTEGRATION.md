# Frontend Integration & API Refactoring Guide

This document explains the refactoring of CV-automation to support a REST API and web dashboard.

## What Changed

### ✅ What's Preserved
- Original CLI pipeline still works: `python main.py`
- All existing modules unchanged
- Backward compatibility maintained
- File-based data storage (JSON)
- Email reporting functionality

### ✨ What's New
- **FastAPI REST API** for programmatic access
- **Web dashboard** for user interaction (`frontend/index.html`)
- **Typed models** (Pydantic) for all API contracts
- **Session management** for tracking multiple pipeline runs
- **Search history tracking** for past searches
- **Real-time progress updates** via polling
- **Job filtering & sorting** endpoints
- **User action tracking** (viewed, applied, dismissed)

---

## Project Structure

### New Files & Directories

```
CV-automation/
├── src/
│   ├── models.py              # ← Pydantic models for API contracts
│   ├── api/                   # ← New API package
│   │   ├── __init__.py
│   │   ├── app.py             # FastAPI application factory
│   │   ├── server.py          # API server entry point
│   │   └── endpoints/         # ← Endpoint modules
│   │       ├── __init__.py
│   │       ├── upload.py      # CV upload
│   │       ├── pipeline.py    # Pipeline orchestration
│   │       ├── results.py     # Job results & filtering
│   │       ├── history.py     # Search history
│   │       └── config.py      # Config management
│   └── recommendation_history.py  # ← Extended with API methods
├── frontend/                  # ← New frontend package
│   └── index.html            # Dashboard SPA
├── temp/                      # ← Uploaded files (created at runtime)
├── docs/                      # ← Documentation
│   └── API_SPEC.md           # REST API specification
└── main.py                    # ← Updated to support both modes
```

---

## Quick Start

### Option 1: Use CLI (Original Way)

```bash
python main.py
```

Works exactly as before. No changes needed.

### Option 2: Use API Server (New Way)

#### Start the API server:
```bash
python main.py --server
# or
python -m src.api.server
```

Server runs at `http://localhost:8000`

#### Access the dashboard:
Open `http://localhost:8000` in your browser

#### Use the API programmatically:
```python
import requests

# Start a pipeline run
response = requests.post("http://localhost:8000/api/pipeline/run", json={
    "use_existing_cv": True,
    "country_filter": "United States",
    "skip_email": True
})
session_id = response.json()["session_id"]

# Poll for status
while True:
    status = requests.get(f"http://localhost:8000/api/pipeline/status/{session_id}").json()
    print(f"Progress: {status['progress_percent']}%")
    
    if status["status"] == "completed":
        break
    time.sleep(2)

# Get filtered jobs
jobs = requests.get(f"http://localhost:8000/api/jobs/{session_id}?min_score=7").json()
print(f"Found {len(jobs['jobs'])} high-scoring jobs")
```

---

## API Usage Examples

### Upload a CV
```bash
curl -X POST http://localhost:8000/api/upload/cv \
  -F "file=@path/to/cv.pdf" \
  -F "auto_parse=true"
```

### Start a Pipeline Run
```bash
curl -X POST http://localhost:8000/api/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{
    "use_existing_cv": true,
    "country_filter": "United States",
    "skip_email": true
  }'
```

### Check Pipeline Status
```bash
curl http://localhost:8000/api/pipeline/status/abc12345
```

### Get Jobs with Filters
```bash
curl "http://localhost:8000/api/jobs/abc12345?min_score=7&country=United%20States&sort_by=score"
```

### Record User Action
```bash
curl -X POST "http://localhost:8000/api/jobs/abc12345/0/action?action=apply"
```

### Get Search History
```bash
curl http://localhost:8000/api/history/?limit=10
```

---

## Data Models

The API uses typed Pydantic models to ensure consistency:

### Key Models

**Profile** - Extracted from CV
```python
Profile(
    name="John Doe",
    email="john@example.com",
    skills=["Python", "React"],
    experience="5 years",
    education="BS Computer Science",
    languages=["English"],
    summary="Full-stack engineer"
)
```

**Job** - Job listing with evaluation results
```python
Job(
    title="Senior Python Engineer",
    company="TechCorp",
    location="San Francisco, CA",
    country="United States",
    score=9,  # 1-10 from LLM
    classification="industry",  # or "research"
    url="https://...",
    source="remotive"
)
```

**SearchSession** - Represents one pipeline run
```python
SearchSession(
    session_id="abc12345",
    status="running",  # pending/running/completed/failed
    current_step=3,
    progress_percent=50,
    results=RankedResults(...)
)
```

**RankedResults** - Complete results from a run
```python
RankedResults(
    all_jobs=[...],  # All jobs sorted by score
    by_country={...},  # Jobs grouped by country
    by_classification={...},  # Jobs grouped by type
    total_count=25
)
```

See `docs/API_SPEC.md` for full specification.

---

## Endpoint Overview

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/upload/cv` | POST | Upload CV file |
| `/pipeline/run` | POST | Start pipeline run |
| `/pipeline/status/{id}` | GET | Check pipeline progress |
| `/pipeline/{id}/report` | GET | Get completed results |
| `/jobs/{id}` | GET | Get filtered jobs |
| `/jobs/{id}/{idx}/action` | POST | Record user action |
| `/jobs/{id}/by-country` | GET | Jobs grouped by country |
| `/jobs/{id}/by-classification` | GET | Jobs grouped by type |
| `/history/` | GET | Get search history |
| `/history/{id}` | GET | Get session history |
| `/history/{id}/actions` | GET | Get user actions |
| `/config/` | GET | Get current config |
| `/config/status` | GET | Check config validity |

---

## Frontend Features

The web dashboard (`frontend/index.html`) includes:

### Upload Section
- Drag-and-drop or file picker
- Auto-parse CV on upload
- Shows extracted profile

### Pipeline Control
- One-click start
- Real-time progress indicator
- Step-by-step status updates
- Job count during search

### Results Dashboard
- Live statistics (total, avg score, top score)
- Advanced filtering:
  - Score range
  - Country
  - Job type (research/industry)
- Sorting by score, title, company, country
- Job cards with key info
- Direct links to job postings

### User Actions
- Mark jobs as viewed
- Apply to jobs
- Dismiss jobs
- Add notes to jobs

### Search History
- Recent searches list
- Stats per search
- Filter by profile/date
- Delete history

### Features
- ✅ Responsive design
- ✅ Dark mode support (can be added)
- ✅ Real-time updates
- ✅ Error handling
- ✅ Mobile-friendly

---

## Configuration

### Environment Variables

```bash
# API Server
CORS_ORIGINS=*              # CORS allowed origins
DEBUG=true                  # Show detailed errors

# (All existing env vars still work)
OPENAI_API_KEY=...
GMAIL_SENDER=...
GMAIL_APP_PASS=...
# etc.
```

### config.py

No changes needed. All existing config still applies.

### API Server Options

```bash
python main.py --server                    # Start on :8000
python main.py --server --port 9000        # Custom port
python main.py --server --reload            # Auto-reload
python main.py --server --host 127.0.0.1   # Custom host
```

---

## Session Management

Sessions are how the API tracks multiple pipeline runs:

1. **Create session**: `POST /pipeline/run` returns `session_id`
2. **Poll status**: `GET /pipeline/status/{session_id}` for progress
3. **Get results**: `GET /pipeline/{session_id}/report` once complete
4. **Record actions**: `POST /jobs/{session_id}/{idx}/action`
5. **Query history**: `GET /history/{session_id}`

Each session is independent. Multiple sessions can run concurrently.

```
User 1: Session "abc12345" → finds 20 jobs
User 2: Session "def67890" → finds 15 jobs
↓
Same backend, different sessions, no conflict
```

---

## Search History

Every pipeline run is recorded in `data/search_history.json`:

```json
[
  {
    "session_id": "abc12345",
    "profile_name": "John Doe",
    "job_count": 25,
    "top_score": 9,
    "searched_at": "2024-01-15T10:30:00",
    "completed_at": "2024-01-15T10:35:00",
    "country_filter": "United States"
  }
]
```

User actions are tracked in `data/user_actions.json`:

```json
[
  {
    "session_id": "abc12345",
    "job_id": "job_hash_123",
    "action": "apply",
    "timestamp": "2024-01-15T10:31:00"
  }
]
```

---

## Backward Compatibility

### CLI Still Works
```bash
python main.py
```

Runs the original 6-step pipeline exactly as before.

### Existing modules unchanged
- `parse_cv.py`
- `job_search.py`
- `evaluate_jobs.py`
- `rank_jobs.py`
- `report_builder.py`
- `email_sender.py`

### Data files still created
- `data/profile.json`
- `data/jobs_raw.json`
- `data/jobs_scored.json`
- `output/report.html`

### Configuration still applies
All values in `config.py` and environment variables work as before.

---

## What to Avoid

### Don't break coupling (as requested)

✅ **Good**: API layer separate, calls existing modules
```
CLI → parse_cv() → job_search() → email_sender()
API → parse_cv() → job_search() → email_sender() ← shared code
```

✅ **Good**: Frontend independent of backend logic
```
Frontend (JavaScript) ← REST API → Backend (Python)
       (no direct imports)
```

❌ **Bad**: Direct frontend-to-backend coupling
```
Frontend trying to import src.parse_cv directly
```

❌ **Bad**: API directly modifying backend modules
```
API changing config.py values that affect other parts
```

---

## Performance Considerations

### Session Storage (In-Memory)
Currently uses Python dict for session storage. For production:
- Switch to Redis: ` _sessions` stored in Redis
- Add TTL: Sessions expire after 24 hours
- Cleanup job: Periodic cleanup of old sessions

### File I/O
Jobs are loaded from JSON files. For large job sets:
- Consider SQLite: Faster queries
- Add pagination: Limit jobs per request
- Cache results: Store computed rankings

### LLM Calls
Evaluation is slow. For testing:
```bash
# Mock LLM responses
DEBUG=true python main.py --server
```

---

## Testing the API

### Using curl
```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/config
```

### Using Python
```python
import requests
response = requests.get("http://localhost:8000/api/config")
print(response.json())
```

### Using JavaScript (from frontend)
```javascript
fetch('/api/config').then(r => r.json()).then(console.log)
```

### Using Postman
Import the API spec from `docs/API_SPEC.md` into Postman

---

## Troubleshooting

### "Address already in use"
```bash
# Port 8000 is taken. Use a different port:
python main.py --server --port 9000
```

### "No module named 'fastapi'"
```bash
# Install dependencies:
pip install -r requirements.txt
```

### "CV upload fails"
```bash
# Check temp directory permissions:
mkdir -p temp
chmod 755 temp
```

### API works but frontend is blank
```bash
# Frontend is served from the API server
# Make sure you access http://localhost:8000
# NOT http://localhost:8000/frontend
```

---

## Future Enhancements

Planned improvements:

- [ ] WebSocket for real-time updates
- [ ] User authentication (JWT)
- [ ] Database persistence (PostgreSQL/SQLite)
- [ ] Advanced filtering UI
- [ ] Job recommendations API
- [ ] Mobile app
- [ ] Slack bot integration
- [ ] Email alerts
- [ ] Bulk operations (apply to multiple jobs)
- [ ] Job comparison tool

---

## Support

For help:
1. Check `docs/API_SPEC.md` for endpoint details
2. Review `frontend/index.html` for client-side implementation
3. Check logs: `DEBUG=true python main.py --server`
4. Open an issue on GitHub

---

## Summary

This refactoring provides:

✅ **Standardized API usage** - REST API with clear contracts
✅ **Typed frontend models** - Pydantic for type safety
✅ **Upload workflow** - Post CV via API or form upload
✅ **Recommendation dashboard** - Beautiful web UI
✅ **Search history** - Track past searches and interactions
✅ **Preserved UX** - Original CLI still works
✅ **No backend coupling** - Frontend is completely decoupled

The system is now **ready for browser automation, mobile apps, CLI clients, and future integrations**!

