"""Unit tests for src/rank_jobs.py."""

import json
import os
import tempfile

import pytest

from src.rank_jobs import rank_jobs


def _write_jobs(jobs: list, path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(jobs, fh)


def test_rank_jobs_sorted_by_score():
    jobs = [
        {"title": "Low", "score": 2, "classification": "industry", "country": "Remote"},
        {"title": "High", "score": 9, "classification": "research", "country": "Remote"},
        {"title": "Mid", "score": 5, "classification": "industry", "country": "United States"},
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as fh:
        json.dump(jobs, fh)
        path = fh.name

    try:
        result = rank_jobs(jobs_scored_path=path)
        all_jobs = result["all_jobs"]
        assert all_jobs[0]["title"] == "High"
        assert all_jobs[1]["title"] == "Mid"
        assert all_jobs[2]["title"] == "Low"
    finally:
        os.unlink(path)


def test_rank_jobs_by_classification():
    jobs = [
        {"title": "A", "score": 7, "classification": "research", "country": "Remote"},
        {"title": "B", "score": 4, "classification": "industry", "country": "Remote"},
        {"title": "C", "score": 6, "classification": "research", "country": "Remote"},
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as fh:
        json.dump(jobs, fh)
        path = fh.name

    try:
        result = rank_jobs(jobs_scored_path=path)
        by_class = result["by_classification"]
        assert "research" in by_class
        assert "industry" in by_class
        assert len(by_class["research"]) == 2
        assert len(by_class["industry"]) == 1
    finally:
        os.unlink(path)


def test_rank_jobs_by_country():
    jobs = [
        {"title": "A", "score": 8, "classification": "industry", "country": "United States"},
        {"title": "B", "score": 6, "classification": "industry", "country": "United Kingdom"},
        {"title": "C", "score": 5, "classification": "research", "country": "United States"},
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as fh:
        json.dump(jobs, fh)
        path = fh.name

    try:
        result = rank_jobs(jobs_scored_path=path)
        by_country = result["by_country"]
        assert "United States" in by_country
        assert "United Kingdom" in by_country
        assert len(by_country["United States"]) == 2
        assert len(by_country["United Kingdom"]) == 1
    finally:
        os.unlink(path)


def test_rank_jobs_empty():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as fh:
        json.dump([], fh)
        path = fh.name

    try:
        result = rank_jobs(jobs_scored_path=path)
        assert result["all_jobs"] == []
        assert result["by_classification"] == {}
        assert result["by_country"] == {}
    finally:
        os.unlink(path)


def test_rank_jobs_missing_fields():
    """Jobs missing score/classification/country should use defaults."""
    jobs = [{"title": "Only title"}]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as fh:
        json.dump(jobs, fh)
        path = fh.name

    try:
        result = rank_jobs(jobs_scored_path=path)
        assert len(result["all_jobs"]) == 1
        assert result["all_jobs"][0]["score"] == 0
    finally:
        os.unlink(path)


def test_rank_jobs_file_not_found():
    with pytest.raises(FileNotFoundError):
        rank_jobs(jobs_scored_path="/nonexistent/path/jobs.json")
