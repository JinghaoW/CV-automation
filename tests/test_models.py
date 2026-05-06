"""Unit tests for src/models.py."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.models import (
    Job,
    Profile,
    RunRecord,
    ScoredJob,
    SearchHistoryEntry,
    UploadResponse,
)


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------


def test_profile_defaults():
    p = Profile()
    assert p.name == ""
    assert p.skills == []
    assert p.experience_years == 0.0
    assert p.education == []
    assert p.languages == []
    assert p.summary == ""


def test_profile_from_dict():
    data = {
        "name": "Jane Doe",
        "skills": ["Python", "ML"],
        "experience_years": 5,
        "education": ["PhD CS"],
        "languages": ["English", "French"],
        "summary": "Experienced ML engineer.",
    }
    p = Profile(**data)
    assert p.name == "Jane Doe"
    assert "Python" in p.skills
    assert p.experience_years == 5.0
    assert "PhD CS" in p.education


def test_profile_extra_fields_ignored():
    """Extra keys in source dict should not cause errors (Pydantic default)."""
    p = Profile(**{"name": "Alice", "unknown_field": "ignored"})
    assert p.name == "Alice"


# ---------------------------------------------------------------------------
# Job / ScoredJob
# ---------------------------------------------------------------------------


def test_job_defaults():
    j = Job()
    assert j.title == ""
    assert j.url == ""


def test_scored_job_defaults():
    j = ScoredJob()
    assert j.score == 0
    assert j.classification == "unknown"
    assert j.reasoning == ""


def test_scored_job_inherits_job_fields():
    j = ScoredJob(
        title="ML Engineer",
        company="ACME",
        score=9,
        classification="industry",
        reasoning="Strong match",
    )
    assert j.title == "ML Engineer"
    assert j.score == 9
    assert j.classification == "industry"


# ---------------------------------------------------------------------------
# UploadResponse
# ---------------------------------------------------------------------------


def test_upload_response():
    r = UploadResponse(message="OK", filename="CV.pdf", cv_path="cv/CV.pdf")
    assert r.message == "OK"
    assert r.filename == "CV.pdf"
    assert r.cv_path == "cv/CV.pdf"


# ---------------------------------------------------------------------------
# RunRecord
# ---------------------------------------------------------------------------


def test_run_record_defaults():
    r = RunRecord(run_id="abc123", started_at=datetime.now(tz=timezone.utc))
    assert r.status == "pending"
    assert r.jobs_found == 0
    assert r.jobs_scored == 0
    assert r.finished_at is None
    assert r.error is None


def test_run_record_accepts_iso_string_for_started_at():
    """Pydantic should coerce an ISO timestamp string to datetime."""
    r = RunRecord(run_id="x", started_at="2024-01-01T07:00:00+00:00")
    assert isinstance(r.started_at, datetime)


# ---------------------------------------------------------------------------
# SearchHistoryEntry
# ---------------------------------------------------------------------------


def test_search_history_entry_from_run_record_dict():
    now_iso = datetime.now(tz=timezone.utc).isoformat()
    entry = SearchHistoryEntry(
        run_id="abc",
        started_at=now_iso,
        status="completed",
        jobs_found=10,
        jobs_scored=8,
    )
    assert entry.run_id == "abc"
    assert entry.status == "completed"
    assert entry.jobs_found == 10
    assert entry.finished_at is None
