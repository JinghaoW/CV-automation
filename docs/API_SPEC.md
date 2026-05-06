# CV-automation API & Frontend Integration

This document describes the REST API and frontend dashboard for CV-automation.

## Quick Start

### 1. Start the API server

```bash
# Install dependencies
pip install -r requirements.txt

# Run API server
python -m src.api.server

# Server will be available at http://localhost:8000
```

### 2. Open the dashboard

Navigate to `http://localhost:8000` in your browser.

---

## API Overview

The REST API provides endpoints for:
- **File uploads**: Upload CV files
- **Pipeline orchestration**: Trigger and monitor pipeline runs
- **Job searching & filtering**: Browse and filter job results
- **Search history**: Track past searches and user actions
- **Configuration**: View and update settings

### Base URL
```
http://localhost:8000/api
```

### Authentication
Currently, no authentication is required. Add JWT/session tokens in future versions if needed.

---

## API Endpoints

### Upload - `/upload`

#### `POST /upload/cv`
Upload a CV file and optionally parse it.

**Parameters:**
- `file` (multipart/form-data): PDF file
- `auto_parse` (boolean, optional): Parse CV immediately. Default: `true`

**Response:**
```json
{
  "success": true,
  "message": "CV uploaded successfully",
  "cv_path": "/path/to/cv.pdf",
  "profile": {
    "name": "John Doe",
    "email": "john@example.com",
    "skills": ["Python", "React", "Docker"],
    "experience": "5 years",
    "education": "BS Computer Science",
    "languages": ["English", "Spanish"],
    "summary": "Full-stack engineer...",
    "cv_path": "/path/to/cv.pdf",
    "extracted_at": "2024-01-15T10:30:00"
  }
}
```

---

### Pipeline - `/pipeline`

#### `POST /pipeline/run`
Trigger a new pipeline run.

**Request Body:**
```json
{
  "use_existing_cv": true,
  "country_filter": "",
  "skip_email": true
}
```

**Response:**
```json
{
  "session_id": "abc12345",
  "message": "Pipeline started",
  "status_url": "/pipeline/abc12345/status"
}
```

#### `GET /pipeline/status/{session_id}`
Get current status of a pipeline run.

**Response:**
```json
{
  "session_id": "abc12345",
  "status": "running",
  "current_step": 3,
  "step_name": "Evaluating jobs",
  "progress_percent": 50,
  "elapsed_seconds": 45.2,
  "error": null,
  "results": null
}
```

**Status values:** `pending`, `running`, `completed`, `failed`

**Step numbers:**
- 0: Initializing
- 1: Parsing CV
- 2: Searching jobs
- 3: Evaluating jobs
- 4: Ranking jobs
- 5: Building report
- 6: Complete

#### `GET /pipeline/{session_id}/report`
Get detailed report from a completed pipeline run.

**Response:**
```json
{
  "session_id": "abc12345",
  "profile": { ... },
  "results": {
    "all_jobs": [ ... ],
    "by_country": { ... },
    "by_classification": { ... },
    "total_count": 25,
    "generated_at": "2024-01-15T10:35:00"
  },
  "completed_at": "2024-01-15T10:35:00"
}
```

---

### Jobs - `/jobs`

#### `GET /jobs/{session_id}`
Get jobs from a session with optional filtering.

**Query Parameters:**
- `min_score` (integer, 1-10): Minimum job score. Default: `1`
- `max_score` (integer, 1-10): Maximum job score. Default: `10`
- `country` (string, optional): Filter by country
- `classification` (string, optional): `research` or `industry`
- `sort_by` (string): `score`, `title`, `company`, `country`. Default: `score`
- `sort_order` (string): `asc` or `desc`. Default: `desc`

**Example:**
```
GET /jobs/abc12345?min_score=7&country=United%20States&sort_by=score&sort_order=desc
```

**Response:**
```json
{
  "jobs": [
    {
      "id": "job_hash_123",
      "title": "Senior Python Engineer",
      "company": "TechCorp",
      "location": "San Francisco, CA",
      "country": "United States",
      "description": "We are looking for...",
      "url": "https://example.com/job/123",
      "source": "remotive",
      "category": "backend",
      "score": 9,
      "reasoning": "Strong match for Python and team lead experience",
      "classification": "industry",
      "viewed": false,
      "applied": false,
      "dismissed": false,
      "notes": ""
    }
  ],
  "total": 15,
  "filters": {
    "min_score": 7,
    "max_score": 10,
    "country": "United States",
    "classification": null
  }
}
```

#### `GET /jobs/{session_id}/{job_index}`
Get detailed information about a specific job.

**Response:**
```json
{
  "job": { ... },
  "index": 0,
  "total": 15,
  "navigation": {
    "prev": null,
    "next": 1
  }
}
```

#### `POST /jobs/{session_id}/{job_index}/action`
Record an action on a job.

**Query Parameters:**
- `action` (string, required): `view`, `apply`, or `dismiss`
- `notes` (string, optional): User notes on the job

**Response:**
```json
{
  "success": true,
  "action": "apply",
  "job": { ... }
}
```

#### `GET /jobs/{session_id}/by-country`
Get jobs grouped by country.

**Response:**
```json
{
  "by_country": {
    "United States": [ ... ],
    "United Kingdom": [ ... ],
    "Remote": [ ... ]
  },
  "total": 25
}
```

#### `GET /jobs/{session_id}/by-classification`
Get jobs grouped by classification (research/industry).

**Response:**
```json
{
  "by_classification": {
    "research": [ ... ],
    "industry": [ ... ]
  },
  "total": 25
}
```

---

### History - `/history`

#### `GET /history/`
Get search history.

**Query Parameters:**
- `limit` (integer): Number of records to return. Max: 100. Default: 50
- `offset` (integer): Pagination offset. Default: 0

**Response:**
```json
{
  "records": [
    {
      "session_id": "abc12345",
      "profile_name": "John Doe",
      "job_count": 25,
      "top_score": 9,
      "searched_at": "2024-01-15T10:30:00",
      "completed_at": "2024-01-15T10:35:00",
      "country_filter": ""
    }
  ],
  "total": 5,
  "limit": 50,
  "offset": 0
}
```

#### `GET /history/{session_id}`
Get history for a specific session.

**Response:**
```json
{
  "session_id": "abc12345",
  "records": [ ... ],
  "total": 1
}
```

#### `GET /history/{session_id}/actions`
Get all user actions (viewed, applied, dismissed) for a session.

**Response:**
```json
{
  "session_id": "abc12345",
  "actions": {
    "viewed": [
      {
        "session_id": "abc12345",
        "job_id": "job_hash_123",
        "action": "view",
        "timestamp": "2024-01-15T10:31:00"
      }
    ],
    "applied": [ ... ],
    "dismissed": [ ... ]
  },
  "total": 12
}
```

#### `POST /history/{session_id}/stats`
Get statistics for a session.

**Response:**
```json
{
  "session_id": "abc12345",
  "stats": {
    "viewed_count": 8,
    "applied_count": 2,
    "dismissed_count": 2,
    "engagement_rate": 0.48
  }
}
```

#### `DELETE /history/{session_id}`
Delete all history for a session.

**Response:**
```json
{
  "message": "Deleted history for session abc12345",
  "session_id": "abc12345"
}
```

---

### Configuration - `/config`

#### `GET /config/`
Get current configuration (non-sensitive values only).

**Response:**
```json
{
  "cv_path": "cv/CV.pdf",
  "country": "",
  "email_subject": "Daily Job Search Report",
  "llm_provider": "openai",
  "llm_model": "gpt-4o-mini",
  "schedule_hour_utc": 7,
  "schedule_minute_utc": 0
}
```

#### `GET /config/providers`
Get list of available LLM providers.

**Response:**
```json
{
  "providers": ["openai", "deepseek", "gemini", "openrouter", "ollama"],
  "current": "openai"
}
```

#### `POST /config/`
Update configuration (session only, not persisted).

**Request Body:**
```json
{
  "country_filter": "United States",
  "email_subject": "My Custom Subject",
  "cv_path": "/path/to/cv.pdf"
}
```

**Response:**
```json
{
  "message": "Configuration updated (session only)",
  "updates": {
    "country": "United States"
  },
  "note": "Changes are not persisted. Edit config.py for permanent changes."
}
```

#### `GET /config/status`
Check configuration validation status.

**Response:**
```json
{
  "valid": true,
  "issues": [],
  "can_search": true,
  "can_email": true
}
```

---

## Data Models

### Profile
```python
{
  "name": str,
  "email": str,
  "skills": list[str],
  "experience": str,
  "education": str,
  "languages": list[str],
  "summary": str,
  "cv_path": str,
  "extracted_at": datetime
}
```

### Job
```python
{
  "id": str,                    # Unique job ID
  "title": str,
  "company": str,
  "location": str,             # Location string
  "country": str,              # Inferred country
  "description": str,          # Full text description
  "url": str,
  "source": str,               # "remotive", "hn", etc
  "category": str,
  "score": int,                # 1-10, from LLM evaluation
  "reasoning": str,            # Why this score
  "classification": str,       # "research" or "industry"
  "viewed": bool,              # User interaction
  "applied": bool,
  "dismissed": bool,
  "notes": str
}
```

### RankedResults
```python
{
  "all_jobs": list[Job],
  "by_country": dict[str, list[Job]],
  "by_classification": dict[str, list[Job]],
  "total_count": int,
  "generated_at": datetime
}
```

### SearchSession
```python
{
  "session_id": str,
  "profile": Profile,
  "created_at": datetime,
  "completed_at": datetime | None,
  "status": str,               # "pending", "running", "completed", "failed"
  "current_step": int,         # 0-6
  "results": RankedResults | None,
  "error": str | None
}
```

---

## Error Handling

All error responses follow this format:

```json
{
  "error": "Error message",
  "error_code": "ERROR_CODE",
  "detail": "Additional details (if DEBUG=true)"
}
```

**Common error codes:**
- `HTTP_ERROR`: HTTP exception
- `VALIDATION_ERROR`: Input validation failed
- `INTERNAL_ERROR`: Unexpected server error

**HTTP Status Codes:**
- `200` OK
- `400` Bad Request (validation failed)
- `404` Not Found
- `500` Internal Server Error

---

## Example Workflow

### 1. Upload CV and start search
```bash
# Upload CV
curl -X POST http://localhost:8000/api/upload/cv \
  -F "file=@cv.pdf" \
  -F "auto_parse=true"

# Response:
{
  "success": true,
  "profile": { ... }
}
```

### 2. Start pipeline
```bash
curl -X POST http://localhost:8000/api/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{
    "use_existing_cv": true,
    "country_filter": "United States",
    "skip_email": true
  }'

# Response:
{
  "session_id": "abc12345",
  "status_url": "/pipeline/abc12345/status"
}
```

### 3. Poll for status
```bash
curl http://localhost:8000/api/pipeline/status/abc12345

# Response:
{
  "status": "completed",
  "current_step": 6,
  "progress_percent": 100,
  "results": { ... }
}
```

### 4. Get filtered jobs
```bash
curl "http://localhost:8000/api/jobs/abc12345?min_score=7&country=United%20States"

# Response:
{
  "jobs": [ ... ],
  "total": 12
}
```

### 5. Record action
```bash
curl -X POST "http://localhost:8000/api/jobs/abc12345/0/action?action=apply"

# Response:
{
  "success": true,
  "action": "apply"
}
```

---

## Frontend Integration

The dashboard (`frontend/index.html`) provides a user-friendly interface for:
- **CV Upload**: Drag-and-drop or file picker
- **Pipeline Control**: Start/stop pipeline runs
- **Live Progress**: Real-time progress updates
- **Job Browsing**: Filter, sort, and view jobs
- **User Actions**: Mark jobs as viewed, applied, or dismissed
- **Search History**: Track past searches

### Features
- ✅ Responsive design (mobile-friendly)
- ✅ Real-time progress tracking
- ✅ Advanced filtering and sorting
- ✅ Search history with stats
- ✅ Job detail view with navigation
- ✅ Direct links to job postings
- ✅ Error handling and user feedback

### Customization
Edit `frontend/index.html` to customize:
- Colors and branding (CSS variables)
- Layout and responsive breakpoints
- Filter options
- API polling interval

---

## Development

### Running in debug mode
```bash
DEBUG=true python -m src.api.server
```

### Running with auto-reload
```bash
python -m src.api.server
# Auto-reloads on file changes
```

### Testing the API
```bash
# Using curl
curl http://localhost:8000/health

# Using Python requests
import requests
response = requests.get("http://localhost:8000/api/config")
print(response.json())

# Using httpie
http GET localhost:8000/api/config
```

---

## Future Enhancements

- [ ] WebSocket support for real-time updates
- [ ] User authentication (JWT)
- [ ] Database persistence (PostgreSQL)
- [ ] Email notifications
- [ ] Job recommendation API
- [ ] Mobile app
- [ ] Slack/Discord integration

---

## Support

For issues or questions, open an issue on GitHub or check the troubleshooting section in README.md.

