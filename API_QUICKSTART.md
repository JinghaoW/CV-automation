# API & Frontend Quick Start

## Installation

```bash
# Install dependencies (includes FastAPI, Uvicorn, Pydantic)
pip install -r requirements.txt
```

## Running the API Server

### Option 1: From main.py
```bash
# Start API server with web dashboard
python main.py --server

# Custom port
python main.py --server --port 9000

# With auto-reload (for development)
python main.py --server --reload
```

### Option 2: Direct with uvicorn
```bash
python -m src.api.server
```

### Option 3: Direct with uvicorn (advanced)
```bash
uvicorn src.api.server:app --reload --host 0.0.0.0 --port 8000
```

## Access the Dashboard

Once the server is running:
- **Dashboard**: http://localhost:8000
- **API Docs (Swagger)**: http://localhost:8000/docs
- **API Docs (ReDoc)**: http://localhost:8000/redoc

## API Endpoints

### Core Workflow
```bash
# 1. Upload a CV
curl -X POST http://localhost:8000/api/upload/cv \
  -F "file=@cv.pdf" \
  -F "auto_parse=true"

# 2. Start a pipeline run
curl -X POST http://localhost:8000/api/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{
    "use_existing_cv": true,
    "country_filter": "United States",
    "skip_email": true
  }'

# Response: {"session_id": "abc12345"}

# 3. Check status
curl http://localhost:8000/api/pipeline/status/abc12345

# 4. Get jobs
curl http://localhost:8000/api/jobs/abc12345?min_score=7

# 5. Record action
curl -X POST http://localhost:8000/api/jobs/abc12345/0/action?action=apply
```

## Using the Dashboard

1. **Upload CV**: Click "Choose CV (PDF)" and upload your CV
2. **Start Search**: Click "Search" to trigger the pipeline
3. **Monitor Progress**: Watch the progress bar update in real-time
4. **Browse Results**: Once complete, filter and sort jobs
5. **Track Actions**: Mark jobs as viewed, applied, or dismissed

## Configuration

All existing config values (from `config.py` and environment variables) are used by the API:
- `OPENAI_API_KEY` - Required for CV parsing and job evaluation
- `GMAIL_SENDER`, `GMAIL_APP_PASS`, `GMAIL_RECIPIENT` - For email features
- `LLM_PROVIDER`, `LLM_MODEL` - For LLM selection
- `COUNTRY` - Filter jobs by region

For full API specification, see `docs/API_SPEC.md`.
For integration details, see `docs/INTEGRATION.md`.

## Troubleshooting

### ModuleNotFoundError: No module named 'fastapi'
```bash
pip install -r requirements.txt
```

### Address already in use on port 8000
```bash
python main.py --server --port 9000
```

### CORS errors in browser
CORS is already configured to allow all origins by default. If you have issues:
```bash
CORS_ORIGINS=http://localhost:3000 python main.py --server
```

## Development Mode

```bash
# Run with auto-reload and debug info
DEBUG=true python main.py --server --reload
```

This will:
- Auto-reload on file changes
- Show detailed error messages
- Disable some optimizations

## Testing the API

### Using curl
```bash
# Health check
curl http://localhost:8000/health

# Get configuration
curl http://localhost:8000/api/config

# Check config status
curl http://localhost:8000/api/config/status
```

### Using Python
```python
import requests

# Get current config
response = requests.get("http://localhost:8000/api/config")
print(response.json())

# Start pipeline
response = requests.post("http://localhost:8000/api/pipeline/run", json={
    "use_existing_cv": True,
    "skip_email": True
})
print(response.json()["session_id"])
```

### Using JavaScript
```javascript
// From browser console
fetch('/api/config').then(r => r.json()).then(console.log)

// Start pipeline
fetch('/api/pipeline/run', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({use_existing_cv: true, skip_email: true})
}).then(r => r.json()).then(console.log)
```

## Next Steps

- Read `docs/API_SPEC.md` for complete endpoint reference
- Read `docs/INTEGRATION.md` for architecture and design decisions
- Customize `frontend/index.html` for your UI needs
- Set up environment variables in `.env` using `.env.example` as template

## Running Original CLI

The original CLI pipeline still works unchanged:
```bash
python main.py
```

This runs the 6-step pipeline without starting the API server.

