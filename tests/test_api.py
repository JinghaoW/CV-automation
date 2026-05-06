"""Unit tests for src/api.py (FastAPI endpoints)."""

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# POST /api/cv/upload
# ---------------------------------------------------------------------------


def test_upload_cv_rejects_non_pdf():
    response = client.post(
        "/api/cv/upload",
        files={"file": ("resume.txt", b"not a pdf", "text/plain")},
    )
    assert response.status_code == 400
    assert "PDF" in response.json()["detail"]


def test_upload_cv_success():
    with tempfile.TemporaryDirectory() as tmpdir:
        cv_dir = os.path.join(tmpdir, "cv")
        with patch("src.api.os.makedirs"), patch(
            "src.api.open", create=True
        ) as mock_open:
            mock_fh = MagicMock()
            mock_open.return_value.__enter__ = lambda s: mock_fh
            mock_open.return_value.__exit__ = lambda s, *a: False

            response = client.post(
                "/api/cv/upload",
                files={"file": ("CV.pdf", b"%PDF-1.4", "application/pdf")},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "CV.pdf"
        assert data["cv_path"].endswith("CV.pdf")


# ---------------------------------------------------------------------------
# GET /api/recommendations
# ---------------------------------------------------------------------------


def test_get_recommendations_no_file():
    """Returns empty list when no scored-jobs file exists."""
    with patch("src.api.os.path.exists", return_value=False):
        response = client.get("/api/recommendations")
    assert response.status_code == 200
    assert response.json() == []


def test_get_recommendations_sorted_by_score():
    scored_jobs = [
        {
            "title": "Researcher",
            "company": "Uni",
            "score": 5,
            "classification": "research",
            "reasoning": "OK",
            "location": "USA",
            "country": "United States",
            "description": "desc",
            "url": "https://uni.edu",
            "source": "hn",
            "category": "",
        },
        {
            "title": "Engineer",
            "company": "Corp",
            "score": 9,
            "classification": "industry",
            "reasoning": "Great",
            "location": "Remote",
            "country": "Remote",
            "description": "desc",
            "url": "https://corp.com",
            "source": "remotive",
            "category": "Software Dev",
        },
    ]
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "jobs_scored.json")
        with open(path, "w") as fh:
            json.dump(scored_jobs, fh)
        with patch("src.api._JOBS_SCORED_PATH", path):
            response = client.get("/api/recommendations")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["score"] == 9  # highest score first
    assert data[1]["score"] == 5


def test_get_recommendations_min_score_filter():
    scored_jobs = [
        {"title": "A", "company": "X", "score": 3, "classification": "industry",
         "reasoning": "", "location": "", "country": "", "description": "",
         "url": "https://x.com", "source": "", "category": ""},
        {"title": "B", "company": "Y", "score": 8, "classification": "industry",
         "reasoning": "", "location": "", "country": "", "description": "",
         "url": "https://y.com", "source": "", "category": ""},
    ]
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "jobs_scored.json")
        with open(path, "w") as fh:
            json.dump(scored_jobs, fh)
        with patch("src.api._JOBS_SCORED_PATH", path):
            response = client.get("/api/recommendations?min_score=7")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "B"


# ---------------------------------------------------------------------------
# GET /api/history
# ---------------------------------------------------------------------------


def test_get_search_history_empty():
    with patch("src.api._load_run_history", return_value=[]):
        response = client.get("/api/history")
    assert response.status_code == 200
    assert response.json() == []


def test_get_search_history_returns_entries_in_reverse_order():
    records = [
        {
            "run_id": "aaa",
            "started_at": "2024-01-01T07:00:00+00:00",
            "finished_at": "2024-01-01T07:05:00+00:00",
            "status": "completed",
            "jobs_found": 20,
            "jobs_scored": 18,
            "error": None,
        },
        {
            "run_id": "bbb",
            "started_at": "2024-01-02T07:00:00+00:00",
            "finished_at": "2024-01-02T07:05:00+00:00",
            "status": "completed",
            "jobs_found": 30,
            "jobs_scored": 25,
            "error": None,
        },
    ]
    with patch("src.api._load_run_history", return_value=records):
        response = client.get("/api/history")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["run_id"] == "bbb"  # most recent first


# ---------------------------------------------------------------------------
# GET /api/report
# ---------------------------------------------------------------------------


def test_get_report_not_found():
    with patch("src.api.os.path.exists", return_value=False):
        response = client.get("/api/report")
    assert response.status_code == 404


def test_get_report_success():
    html_content = "<html><body><h1>Report</h1></body></html>"
    with tempfile.TemporaryDirectory() as tmpdir:
        report_path = os.path.join(tmpdir, "report.html")
        with open(report_path, "w") as fh:
            fh.write(html_content)
        with patch("src.api._REPORT_PATH", report_path), patch(
            "src.api.os.path.exists", return_value=True
        ):
            response = client.get("/api/report")
    assert response.status_code == 200
    assert "Report" in response.text


# ---------------------------------------------------------------------------
# GET /api/profile
# ---------------------------------------------------------------------------


def test_get_profile_not_found():
    with patch("src.api.os.path.exists", return_value=False):
        response = client.get("/api/profile")
    assert response.status_code == 404


def test_get_profile_success():
    profile = {
        "name": "Jane Doe",
        "skills": ["Python", "ML"],
        "experience_years": 5,
        "education": ["PhD CS"],
        "languages": ["English"],
        "summary": "Experienced engineer.",
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "profile.json")
        with open(path, "w") as fh:
            json.dump(profile, fh)
        with patch("src.api.os.path.exists", return_value=True), patch(
            "src.api.open", create=True
        ) as mock_open:
            mock_open.return_value.__enter__ = lambda s: open(path)
            mock_open.return_value.__exit__ = lambda s, *a: False
            # Use a simpler approach: patch os.path.join for the profile path
            with patch("src.api.os.path.join", return_value=path):
                response = client.get("/api/profile")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Jane Doe"
    assert "Python" in data["skills"]


# ---------------------------------------------------------------------------
# PATCH /api/recommendations/{job_hash}/status
# ---------------------------------------------------------------------------


def test_update_recommendation_status_invalid():
    mock_history = MagicMock()
    with patch("src.api._get_recommendation_history", return_value=mock_history):
        response = client.patch(
            "/api/recommendations/abc123/status?status=nonexistent"
        )
    assert response.status_code == 400
    assert "Invalid status" in response.json()["detail"]


def test_update_recommendation_status_not_found():
    mock_history = MagicMock()
    mock_history.update_status.return_value = False
    with patch("src.api._get_recommendation_history", return_value=mock_history):
        response = client.patch(
            "/api/recommendations/unknown_hash/status?status=viewed"
        )
    assert response.status_code == 404


def test_update_recommendation_status_success():
    mock_history = MagicMock()
    mock_history.update_status.return_value = True
    with patch("src.api._get_recommendation_history", return_value=mock_history):
        response = client.patch(
            "/api/recommendations/abc123/status?status=applied"
        )
    assert response.status_code == 200
    data = response.json()
    assert data["job_hash"] == "abc123"
    assert data["status"] == "applied"
