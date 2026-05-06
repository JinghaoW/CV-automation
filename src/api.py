"""FastAPI application providing standardized API endpoints for CV-automation.

Endpoints
---------
POST  /api/cv/upload                          Upload a CV PDF
POST  /api/run                                Trigger the full pipeline
GET   /api/recommendations                    Recommendation dashboard (JSON)
GET   /api/history                            Search history (JSON)
GET   /api/report                             Latest HTML report
GET   /api/profile                            Current candidate profile
PATCH /api/recommendations/{job_hash}/status  Update recommendation status
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse

import config
from src.models import (
    Profile,
    RunRecord,
    ScoredJob,
    SearchHistoryEntry,
    UploadResponse,
)
from src.recommendation_history import RecommendationHistory, stable_job_hash

app = FastAPI(
    title="CV-automation API",
    description="Standardized API for the CV-automation job search pipeline.",
    version="1.0.0",
)

_RUN_HISTORY_PATH = os.path.join("data", "run_history.json")
_JOBS_SCORED_PATH = os.path.join("data", "jobs_scored.json")
_REPORT_PATH = os.path.join("output", "report.html")
_RECOMMENDATION_HISTORY_PATH = os.path.join("data", "recommendation_history.json")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_recommendation_history() -> RecommendationHistory:
    """Return a ``RecommendationHistory`` instance backed by the standard path."""
    return RecommendationHistory(path=_RECOMMENDATION_HISTORY_PATH)


def _load_run_history() -> list[dict]:
    if os.path.exists(_RUN_HISTORY_PATH):
        with open(_RUN_HISTORY_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    return []


def _save_run_history(records: list[dict]) -> None:
    os.makedirs("data", exist_ok=True)
    with open(_RUN_HISTORY_PATH, "w", encoding="utf-8") as fh:
        json.dump(records, fh, indent=2, ensure_ascii=False, default=str)


def _upsert_run_record(run_id: str, record: dict) -> None:
    """Insert or replace a run record identified by *run_id*."""
    history = _load_run_history()
    for i, r in enumerate(history):
        if r.get("run_id") == run_id:
            history[i] = record
            _save_run_history(history)
            return
    history.append(record)
    _save_run_history(history)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.post("/api/cv/upload", response_model=UploadResponse)
async def upload_cv(file: UploadFile = File(...)) -> UploadResponse:
    """Upload a CV PDF file to the ``cv/`` directory.

    The uploaded file replaces any existing file with the same name.
    Only ``.pdf`` files are accepted.
    """
    filename = file.filename or ""
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    os.makedirs("cv", exist_ok=True)
    cv_path = os.path.join("cv", filename)
    content = await file.read()
    with open(cv_path, "wb") as fh:
        fh.write(content)

    return UploadResponse(
        message="CV uploaded successfully.",
        filename=filename,
        cv_path=cv_path,
    )


@app.post("/api/run", response_model=RunRecord)
async def trigger_run(cv_filename: Optional[str] = None) -> RunRecord:
    """Trigger the full CV-automation pipeline.

    If *cv_filename* is provided the pipeline uses ``cv/<cv_filename>``;
    otherwise it falls back to the ``CV_PATH`` configured in ``config.py``.

    The pipeline runs in a background thread so the event loop stays free.
    A ``RunRecord`` is persisted to ``data/run_history.json`` and returned.
    """
    cv_path = os.path.join("cv", cv_filename) if cv_filename else config.CV_PATH
    run_id = str(uuid.uuid4())[:8]
    started_at = datetime.now(tz=timezone.utc)

    record: dict = {
        "run_id": run_id,
        "started_at": started_at.isoformat(),
        "finished_at": None,
        "status": "running",
        "jobs_found": 0,
        "jobs_scored": 0,
        "error": None,
    }
    _upsert_run_record(run_id, record)

    try:
        from src.parse_cv import parse_cv
        from src.job_search import run as search_jobs
        from src.evaluate_jobs import evaluate_jobs
        from src.report_builder import build_report

        await asyncio.to_thread(parse_cv, cv_path)
        raw_jobs: list[dict] = await asyncio.to_thread(search_jobs)
        record["jobs_found"] = len(raw_jobs)

        scored_jobs: list[dict] = await asyncio.to_thread(evaluate_jobs)
        record["jobs_scored"] = len(scored_jobs)

        await asyncio.to_thread(build_report)

        # Record newly seen jobs in recommendation history
        history = _get_recommendation_history()
        for job in scored_jobs:
            h = stable_job_hash(job)
            history.add_recommendation(h, job)

        record["status"] = "completed"
    except Exception as exc:  # noqa: BLE001
        record["status"] = "failed"
        record["error"] = f"{type(exc).__name__}: {exc}"

    record["finished_at"] = datetime.now(tz=timezone.utc).isoformat()
    _upsert_run_record(run_id, record)

    return RunRecord(**record)


@app.get("/api/recommendations", response_model=list[ScoredJob])
async def get_recommendations(min_score: int = 0) -> list[ScoredJob]:
    """Return scored job recommendations sorted by score descending.

    Pass ``?min_score=<n>`` to filter out jobs below a threshold.
    """
    if not os.path.exists(_JOBS_SCORED_PATH):
        return []
    with open(_JOBS_SCORED_PATH, encoding="utf-8") as fh:
        jobs: list[dict] = json.load(fh)

    filtered = (j for j in jobs if int(j.get("score", 0)) >= min_score)
    return [
        ScoredJob(**j)
        for j in sorted(filtered, key=lambda j: int(j.get("score", 0)), reverse=True)
    ]


@app.get("/api/history", response_model=list[SearchHistoryEntry])
async def get_search_history() -> list[SearchHistoryEntry]:
    """Return the list of past pipeline runs in reverse-chronological order."""
    records = _load_run_history()
    return [SearchHistoryEntry(**r) for r in reversed(records)]


@app.get("/api/report", response_class=HTMLResponse)
async def get_report() -> HTMLResponse:
    """Serve the latest HTML job search report."""
    if not os.path.exists(_REPORT_PATH):
        raise HTTPException(status_code=404, detail="No report available yet. Trigger a run first.")
    with open(_REPORT_PATH, encoding="utf-8") as fh:
        content = fh.read()
    return HTMLResponse(content=content)


@app.get("/api/profile", response_model=Profile)
async def get_profile() -> Profile:
    """Return the current candidate profile extracted from the CV."""
    path = os.path.join("data", "profile.json")
    if not os.path.exists(path):
        raise HTTPException(
            status_code=404,
            detail="No profile available yet. Upload a CV and trigger a run first.",
        )
    with open(path, encoding="utf-8") as fh:
        data: dict = json.load(fh)
    return Profile(**data)


@app.patch("/api/recommendations/{job_hash}/status")
async def update_recommendation_status(job_hash: str, status: str) -> dict:
    """Update the status of a job recommendation.

    Valid status values: ``viewed``, ``applied``, ``dismissed``.
    The ``recommended`` status is the initial state set by the system and
    cannot be set through this endpoint.
    """
    valid = {"viewed", "applied", "dismissed"}
    if status not in valid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{status}'. Must be one of: {sorted(valid)}.",
        )
    history = _get_recommendation_history()
    if not history.update_status(job_hash, status):
        raise HTTPException(status_code=404, detail=f"Recommendation '{job_hash}' not found.")
    return {"job_hash": job_hash, "status": status}
