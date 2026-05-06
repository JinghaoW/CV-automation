# Testing & Validation Guide

Follow this guide to verify the frontend integration refactoring is working correctly.

## Prerequisites

- Python 3.11+ installed
- Virtual environment activated
- Dependencies installed: `pip install -r requirements.txt`
- OpenAI API key configured (for full testing)

## Quick Tests (No API Key Required)

### 1. Import Test
```bash
python -c "from src.models import Profile, Job, RankedResults; print('✓ Models OK')"
python -c "from src.api.app import create_app; print('✓ API OK')"
python -c "from src.recommendation_history import RecommendationHistory; print('✓ History OK')"
```

**Expected:** All three commands complete without errors.

### 2. Help Test
```bash
python main.py --help
```

**Expected output should include:**
```
--server     Run as API server instead of CLI pipeline
--port PORT  Port for API server (default: 8000)
--host HOST  Host for API server (default: 0.0.0.0)
--reload     Auto-reload API server on file changes
```

### 3. Start API Server (No API Key Needed)
```bash
python main.py --server
```

**Expected output:**
```
[main] Starting API server on http://0.0.0.0:8000
[main] Dashboard: http://0.0.0.0:8000/
[main] API docs: http://0.0.0.0:8000/docs
[main] Press Ctrl+C to stop
```

Press Ctrl+C to stop.

### 4. Test Health Endpoint
In another terminal while server is running:

```bash
# Windows PowerShell
Invoke-WebRequest http://localhost:8000/health | ConvertFrom-Json

# Or with curl
curl http://localhost:8000/health
```

**Expected:**
```json
{"status": "healthy"}
```

### 5. Test API Documentation
Navigate to:
- `http://localhost:8000/docs` - Swagger UI
- `http://localhost:8000/redoc` - ReDoc

You should see the full API documentation with all endpoints listed.

### 6. Test Dashboard Access
Navigate to:
- `http://localhost:8000/`

You should see the CV-automation dashboard with:
- Upload section
- Recent searches section
- Job results section (initially empty)

## Functional Tests (With API Key)

If you have `OPENAI_API_KEY` configured:

### 7. Configuration Test
```bash
curl http://localhost:8000/api/config
```

**Expected:** JSON response with configuration values.

### 8. Configuration Status Test
```bash
curl http://localhost:8000/api/config/status
```

**Expected:** JSON showing config validity and available features.

### 9. Upload Test
Create a test PDF or use an existing CV:

```bash
curl -X POST http://localhost:8000/api/upload/cv \
  -F "file=@path/to/cv.pdf" \
  -F "auto_parse=true"
```

**Expected:** JSON response with file path and extracted profile.

### 10. Pipeline Test
```bash
curl -X POST http://localhost:8000/api/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{"use_existing_cv": true, "skip_email": true}'
```

**Expected Output:**
```json
{
  "session_id": "abc12345",
  "message": "Pipeline started",
  "status_url": "/pipeline/abc12345/status"
}
```

### 11. Status Polling Test
Using the session_id from previous test:

```bash
# Run multiple times to see progress
curl http://localhost:8000/api/pipeline/status/abc12345
```

**Expected:** Increasing progress percentage until complete.

### 12. Results Test
Once pipeline completes:

```bash
curl http://localhost:8000/api/jobs/abc12345
```

**Expected:** List of found jobs with scores.

### 13. History Test
```bash
curl http://localhost:8000/api/history/
```

**Expected:** List of search history records.

## Browser Testing

### Setup
1. Start API server: `python main.py --server`
2. Open browser: `http://localhost:8000`

### Manual Tests

#### Test 1: Upload Flow
1. Click "Choose CV (PDF)"
2. Select a PDF file
3. Click "Upload"
4. Verify file is uploaded and profile is extracted

**Pass criteria:** Success message appears

#### Test 2: Pipeline Flow
1. Click "Search"
2. Watch progress bar update
3. See results appear when complete

**Pass criteria:** Progress bar reaches 100%, results display

#### Test 3: Filtering
1. After results appear, adjust:
   - Min/Max Score sliders
   - Country dropdown
   - Type dropdown
2. Jobs list should update in real-time

**Pass criteria:** Jobs list updates instantly with filters

#### Test 4: Job Interactions
1. Click "View Job" on any job card
2. Click "Apply" on another job
3. Click "Dismiss" on another job

**Pass criteria:** Actions are recorded

#### Test 5: History
1. Complete a few searches
2. Check "Recent Searches" sidebar

**Pass criteria:** All searches appear in history

#### Test 6: Mobile Responsiveness
1. Open DevTools (F12)
2. Toggle device toolbar
3. Resize to mobile size (320px width)
4. Verify layout is readable

**Pass criteria:** All UI elements remain accessible and readable

## Performance Tests

### Load Test
```bash
# Install Apache Bench (if needed)
# Then run:
ab -n 100 -c 10 http://localhost:8000/health
```

### Memory Test
Start the server and monitor memory usage:
```bash
# Windows
[System.Diagnostics.Process]::GetProcessesByName("python") | Select-Object -ExpandProperty WorkingSet64
```

## Backward Compatibility Tests

### Test 1: CLI Still Works
```bash
python main.py
```

**Expected:** Original pipeline runs without changes

### Test 2: Data Files Created
After CLI run, verify:
```bash
# Check files exist
ls -la data/profile.json data/jobs_raw.json data/jobs_scored.json
```

**Expected:** All three files exist

### Test 3: Configuration Still Works
```bash
# Set environment variable
set COUNTRY=United States
python main.py
```

**Expected:** Pipeline respects COUNTRY filter

## Error Handling Tests

### Test 1: Invalid File Upload
```bash
curl -X POST http://localhost:8000/api/upload/cv \
  -F "file=@test.txt"
```

**Expected:** 400 error with clear message

### Test 2: Non-existent Session
```bash
curl http://localhost:8000/api/jobs/nonexistent
```

**Expected:** 404 error

### Test 3: Invalid Parameters
```bash
curl "http://localhost:8000/api/jobs/abc12345?min_score=15"
```

**Expected:** 422 validation error

## Security Tests

### Test 1: CORS Headers
```bash
curl -i -H "Origin: http://example.com" \
  -H "Access-Control-Request-Method: POST" \
  http://localhost:8000/api/config
```

**Expected:** CORS headers present in response

### Test 2: XSS Protection
Upload a CV with special characters and verify frontend escapes them:

Open browser DevTools and check HTML isn't actually executing any scripts.

### Test 3: File Upload Security
Try uploading a .exe or other non-PDF file.

**Expected:** Rejected with error message

## Integration Tests

### Test 1: Full Workflow
1. Upload CV
2. Start pipeline
3. Monitor progress
4. Filter results
5. Record action
6. Check history

**Expected:** All steps work together seamlessly

### Test 2: Multiple Sessions
1. Open two browser tabs
2. Start different searches in each
3. Verify they don't interfere

**Expected:** Independent results in each tab

### Test 3: Concurrent Requests
```bash
# Terminal 1
curl -X POST http://localhost:8000/api/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{"use_existing_cv": true}'

# Terminal 2 (while 1 is running)
curl http://localhost:8000/api/config
```

**Expected:** Both complete successfully

## Documentation Tests

### Test 1: API Docs Generation
```bash
curl http://localhost:8000/openapi.json | python -m json.tool
```

**Expected:** Valid OpenAPI schema

### Test 2: Read Guides
Verify all documentation files are readable:
- `docs/API_SPEC.md`
- `docs/INTEGRATION.md`
- `API_QUICKSTART.md`
- `REFACTORING_SUMMARY.md`

**Expected:** All files open and contain valuable information

## Automated Tests

Run existing test suite:
```bash
pytest tests/ -v
```

**Expected:** All tests pass (or same as before refactoring)

## Production Tests

### Test 1: Gunicorn Deployment
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 src.api.server:app &
curl http://localhost:8000/health
```

### Test 2: Environment Variables
```bash
set DEBUG=true
set CORS_ORIGINS=http://localhost:3000,http://localhost:5000
python main.py --server
```

**Expected:** Settings applied correctly

## Checklist Summary

Before declaring success:

- [ ] Health check works
- [ ] API docs display correctly
- [ ] Dashboard loads at root URL
- [ ] File upload functions
- [ ] Pipeline can be triggered
- [ ] Progress updates in real-time
- [ ] Results display with filtering
- [ ] History records searches
- [ ] Mobile view is responsive
- [ ] CLI still works (`python main.py`)
- [ ] Data files created correctly
- [ ] No errors in browser console
- [ ] No errors in terminal output
- [ ] API responds with proper JSON
- [ ] Error handling works
- [ ] Documentation is complete

## Troubleshooting

### Server won't start
```bash
# Check port is not in use
netstat -ano | findstr :8000

# Try different port
python main.py --server --port 9000
```

### ModuleNotFoundError
```bash
# Reinstall dependencies
pip install -r requirements.txt

# Verify FastAPI installed
python -c "import fastapi; print(fastapi.__version__)"
```

### Dashboard not loading
```bash
# Verify frontend file exists
ls -la frontend/index.html

# Check server is running
curl http://localhost:8000/health
```

### Session not found error
```bash
# Sessions are stored in memory and reset on server restart
# Start a new pipeline run to get a new session_id
```

## Next Steps

If all tests pass:
1. ✅ Review the refactoring is complete
2. ✅ Deploy to your environment
3. ✅ Share with team
4. ✅ Gather feedback
5. ✅ Plan future enhancements

See `COMPLETION_CHECKLIST.md` for all deliverables.

