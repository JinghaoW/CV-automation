"""Unit tests for src/report_builder.py."""

import json
import os
import tempfile

import pytest

from src.report_builder import build_report, _score_class, _render_job_card


def test_score_class_high():
    assert _score_class(7) == "score-high"
    assert _score_class(10) == "score-high"


def test_score_class_mid():
    assert _score_class(4) == "score-mid"
    assert _score_class(6) == "score-mid"


def test_score_class_low():
    assert _score_class(0) == "score-low"
    assert _score_class(3) == "score-low"


def test_render_job_card_contains_fields():
    job = {
        "title": "Data Scientist",
        "company": "ACME Corp",
        "location": "Remote",
        "score": 8,
        "classification": "research",
        "reasoning": "Good match",
        "url": "https://example.com/job/1",
    }
    card = _render_job_card(job)
    assert "Data Scientist" in card
    assert "ACME Corp" in card
    assert "Remote" in card
    assert "8/10" in card
    assert "research" in card
    assert "Good match" in card
    assert "https://example.com/job/1" in card
    assert "score-high" in card


def test_render_job_card_no_url():
    job = {
        "title": "Engineer",
        "company": "Startup",
        "location": "Berlin",
        "score": 3,
        "classification": "industry",
        "reasoning": "Partial match",
        "url": "",
    }
    card = _render_job_card(job)
    assert "<a href=" not in card
    assert "Engineer" in card
    assert "score-low" in card


def test_render_job_card_xss_escaping():
    """HTML special characters in job fields must be escaped."""
    job = {
        "title": "<script>alert(1)</script>",
        "company": "Bad & Co.",
        "location": "Here > There",
        "score": 5,
        "classification": "industry",
        "reasoning": 'A "quoted" reason',
        "url": "",
    }
    card = _render_job_card(job)
    assert "<script>" not in card
    assert "&lt;script&gt;" in card
    assert "&amp;" in card


def test_build_report_empty_jobs():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as fh:
        json.dump([], fh)
        jobs_path = fh.name

    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as fh:
        report_path = fh.name

    try:
        html = build_report(jobs_scored_path=jobs_path, report_path=report_path)
        assert "No jobs found" in html
        assert os.path.exists(report_path)
    finally:
        os.unlink(jobs_path)
        os.unlink(report_path)


def test_build_report_with_jobs():
    jobs = [
        {
            "title": "ML Engineer",
            "company": "TechCo",
            "location": "Remote",
            "country": "Remote",
            "score": 9,
            "classification": "research",
            "reasoning": "Great fit",
            "url": "https://example.com/1",
        },
        {
            "title": "Backend Dev",
            "company": "StartupX",
            "location": "London",
            "country": "United Kingdom",
            "score": 5,
            "classification": "industry",
            "reasoning": "Decent match",
            "url": "https://example.com/2",
        },
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as fh:
        json.dump(jobs, fh)
        jobs_path = fh.name

    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as fh:
        report_path = fh.name

    try:
        html = build_report(jobs_scored_path=jobs_path, report_path=report_path)
        assert "ML Engineer" in html
        assert "Backend Dev" in html
        assert "Remote" in html
        assert "United Kingdom" in html
        assert "2 listings found" in html
    finally:
        os.unlink(jobs_path)
        os.unlink(report_path)


def test_build_report_file_not_found():
    with pytest.raises(FileNotFoundError):
        build_report(jobs_scored_path="/nonexistent/jobs.json", report_path="/tmp/report.html")
