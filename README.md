# CV-automation

CV-automation reads a CV PDF, finds relevant jobs, scores them with an LLM, builds an HTML report, and can email that report to you.

It supports three ways of using the project:

1. `CLI pipeline`: run the full workflow locally.
2. `API server`: upload a CV and trigger runs over HTTP.
3. `Scheduled runs`: use GitHub Actions or Celery for recurring execution.

## What it does

The default pipeline runs these steps:

1. `parse_cv`: extract a structured profile from your CV.
2. `job_search`: fetch jobs from supported sources.
3. `evaluate_jobs`: score each job against your profile.
4. `rank_jobs`: sort and group the results.
5. `report_builder`: write `output/report.html`.
6. `email_sender`: send the report through Gmail SMTP.

Generated files:

- `data/profile.json`
- `data/jobs_raw.json`
- `data/jobs_scored.json`
- `output/report.html`

## Requirements

- Python `3.11+`
- A CV PDF
- An LLM API key
  - Default provider: OpenAI
- Gmail credentials if you want email delivery
  - `GMAIL_SENDER`
  - `GMAIL_APP_PASS`
  - `GMAIL_RECIPIENT`

## Installation

```bash
git clone https://github.com/JinghaoW/CV-automation.git
cd CV-automation
python -m venv .venv
```

Activate the virtual environment:

```bash
# macOS / Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

The project reads settings from:

1. environment variables
2. `config.py`

Environment variables take precedence.

The fastest setup is to create a `.env` file from `.env.example` and fill in the values you need.

Minimum configuration for the CLI pipeline:

```env
OPENAI_API_KEY=sk-...
CV_PATH=cv/CV.pdf
GMAIL_SENDER=your-email@gmail.com
GMAIL_APP_PASS=your-16-char-app-password
GMAIL_RECIPIENT=recipient@example.com
```

Useful optional settings:

```env
COUNTRY=United States
EMAIL_SUBJECT=Daily Job Search Report
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
```

Notes:

- `CV_PATH` defaults to `cv/CV.pdf`
- Leaving `COUNTRY` blank disables location filtering
- If you do not want to send email, you can still generate the report locally

## Quick Start

Place your CV PDF at:

```text
cv/CV.pdf
```

Then run:

```bash
python main.py
```

If the run succeeds, open:

```text
output/report.html
```

If email delivery is configured, the report is also sent to `GMAIL_RECIPIENT`.

## Running the CLI Pipeline

Run the full workflow:

```bash
python main.py
```

Run modules individually for debugging:

```bash
python -m src.parse_cv
python -m src.job_search
python -m src.evaluate_jobs
python -m src.rank_jobs
python -m src.report_builder
python -m src.email_sender
```

Expected behavior:

- failures in parsing, search, evaluation, ranking, or report generation stop the run
- email failure is treated as non-fatal if the report was already generated

## Running the API Server

Start the server:

```bash
python main.py --server
```

Or with custom host/port:

```bash
python main.py --server --host 0.0.0.0 --port 8000 --reload
```

Useful URLs:

- `http://localhost:8000/`
- `http://localhost:8000/docs`
- `http://localhost:8000/health`

Alternative server entrypoint:

```bash
python -m src.api.server
```

## Basic API Workflow

1. Start the API server.
2. Upload a CV with `POST /upload/cv`.
3. Start a run with `POST /pipeline/run`.
4. Poll `GET /pipeline/status/{session_id}`.
5. Read results from:
   - `GET /pipeline/{session_id}/report`
   - `GET /jobs/{session_id}`

Example with `curl`:

```bash
curl -X POST "http://localhost:8000/pipeline/run" ^
  -H "Content-Type: application/json" ^
  -d "{\"use_existing_cv\": true, \"skip_email\": true}"
```

On macOS/Linux:

```bash
curl -X POST "http://localhost:8000/pipeline/run" \
  -H "Content-Type: application/json" \
  -d '{"use_existing_cv": true, "skip_email": true}'
```

## Scheduled Runs

### GitHub Actions

The repository includes:

```text
.github/workflows/daily_job_search.yml
```

It runs daily at `07:00 UTC` and also supports manual execution.

Repository secrets you need:

- `OPENAI_API_KEY`
- `GMAIL_SENDER`
- `GMAIL_APP_PASS`
- `GMAIL_RECIPIENT`
- `CV_BASE64`

To create `CV_BASE64` in PowerShell:

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("CV.pdf"))
```

### Celery

The project also contains Celery task wiring.

Required services/settings:

- Redis
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`

Example:

```env
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

## Testing

Run tests with:

```bash
python -m pytest tests/ -v
```

If you are using the local virtual environment on Windows:

```bash
.\.venv\Scripts\python.exe -m pytest tests/ -v
```

## Project Layout

```text
CV-automation/
├── config.py
├── main.py
├── cv/
├── data/
├── output/
├── src/
│   ├── api/
│   ├── agents/
│   ├── tasks/
│   ├── parse_cv.py
│   ├── job_search.py
│   ├── evaluate_jobs.py
│   ├── rank_jobs.py
│   ├── report_builder.py
│   ├── email_sender.py
│   ├── llm_client.py
│   ├── matching.py
│   ├── recommendation_history.py
│   └── vector_store.py
└── tests/
```

## Troubleshooting

`CV file not found`

- verify `CV_PATH`
- check that the file exists and is readable

`OPENAI_API_KEY is not set`

- export the variable or add it to `.env`
- if you are using another provider, also verify `LLM_PROVIDER` and related keys

`Report file not found`

- the earlier pipeline stages likely failed
- rerun `python main.py` and inspect the first fatal step

`Email send failed`

- verify Gmail app password setup
- confirm `GMAIL_SENDER` and `GMAIL_RECIPIENT`
- the report can still be read from `output/report.html`

## Current Notes

- The CLI path is the simplest way to use the project today.
- The API and scheduler paths exist, but they are better treated as development or internal tooling surfaces unless you harden deployment, auth, and persistence for production use.
