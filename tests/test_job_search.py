"""Unit tests for src/job_search.py."""

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from src.job_search import _infer_country, search_jobs, run


# ---------------------------------------------------------------------------
# _infer_country
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("location,expected", [
    ("USA", "United States"),
    ("United States", "United States"),
    ("US only", "United States"),
    ("uk", "United Kingdom"),
    ("United Kingdom", "United Kingdom"),
    ("Canada", "Canada"),
    ("Germany", "Germany"),
    ("France", "France"),
    ("Australia", "Australia"),
    ("Remote", "Remote"),
    ("Worldwide", "Remote"),
    ("Anywhere", "Remote"),
    ("Singapore", "Singapore"),          # unknown → returns raw value
    ("", "Unknown"),                     # empty → "Unknown"
])
def test_infer_country(location, expected):
    assert _infer_country(location) == expected


# ---------------------------------------------------------------------------
# search_jobs – country filtering
# ---------------------------------------------------------------------------

_SAMPLE_JOBS = [
    {"title": "A", "company": "X", "location": "Remote", "country": "Remote",
     "description": "desc", "url": "https://a.com", "source": "remotive", "category": ""},
    {"title": "B", "company": "Y", "location": "New York, USA", "country": "United States",
     "description": "desc", "url": "https://b.com", "source": "remotive", "category": ""},
    {"title": "C", "company": "Z", "location": "Berlin", "country": "Germany",
     "description": "desc", "url": "https://c.com", "source": "remotive", "category": ""},
]


@patch("src.job_search.search_remotive")
@patch("src.job_search.search_hn_who_is_hiring")
@patch("src.job_search.config")
def test_search_jobs_no_filter(mock_config, mock_hn, mock_remotive):
    mock_config.COUNTRY = ""
    mock_remotive.return_value = _SAMPLE_JOBS
    mock_hn.return_value = []

    profile = {"skills": ["Python", "ML"]}
    result = search_jobs(profile)
    assert len(result) == 3


@patch("src.job_search.search_remotive")
@patch("src.job_search.search_hn_who_is_hiring")
@patch("src.job_search.config")
def test_search_jobs_country_filter(mock_config, mock_hn, mock_remotive):
    mock_config.COUNTRY = "United States"
    mock_remotive.return_value = _SAMPLE_JOBS
    mock_hn.return_value = []

    profile = {"skills": ["Python"]}
    result = search_jobs(profile)
    assert len(result) == 1
    assert result[0]["title"] == "B"


@patch("src.job_search.search_remotive")
@patch("src.job_search.search_hn_who_is_hiring")
@patch("src.job_search.config")
def test_search_jobs_country_filter_case_insensitive(mock_config, mock_hn, mock_remotive):
    mock_config.COUNTRY = "remote"
    mock_remotive.return_value = _SAMPLE_JOBS
    mock_hn.return_value = []

    profile = {"skills": ["Python"]}
    result = search_jobs(profile)
    assert len(result) == 1
    assert result[0]["title"] == "A"


@patch("src.job_search.search_remotive")
@patch("src.job_search.search_hn_who_is_hiring")
@patch("src.job_search.config")
def test_search_jobs_deduplication(mock_config, mock_hn, mock_remotive):
    """Jobs with the same URL should be deduplicated."""
    mock_config.COUNTRY = ""
    duplicate = dict(_SAMPLE_JOBS[0])  # same URL as _SAMPLE_JOBS[0]
    mock_remotive.return_value = [_SAMPLE_JOBS[0], duplicate]
    mock_hn.return_value = []

    profile = {"skills": ["Python"]}
    result = search_jobs(profile)
    assert len(result) == 1


@patch("src.job_search.search_remotive")
@patch("src.job_search.search_hn_who_is_hiring")
@patch("src.job_search.config")
def test_search_jobs_no_skills_raises(mock_config, mock_hn, mock_remotive):
    mock_config.COUNTRY = ""
    mock_remotive.return_value = []
    mock_hn.return_value = []

    with pytest.raises(ValueError, match="no skills"):
        search_jobs({"skills": []})


# ---------------------------------------------------------------------------
# run – integration with file I/O
# ---------------------------------------------------------------------------

@patch("src.job_search.search_jobs")
def test_run_saves_jobs(mock_search_jobs):
    mock_search_jobs.return_value = [
        {"title": "X", "url": "https://x.com", "source": "remotive"}
    ]

    profile = {"skills": ["Python"]}
    with tempfile.TemporaryDirectory() as tmpdir:
        profile_path = os.path.join(tmpdir, "profile.json")
        jobs_path = os.path.join(tmpdir, "jobs_raw.json")
        with open(profile_path, "w") as fh:
            json.dump(profile, fh)

        with patch("src.job_search.JOBS_RAW_PATH", jobs_path):
            result = run(profile_path=profile_path)

        assert len(result) == 1
        assert os.path.exists(jobs_path)
        with open(jobs_path) as fh:
            saved = json.load(fh)
        assert saved[0]["title"] == "X"


def test_run_missing_profile():
    with pytest.raises(FileNotFoundError):
        run(profile_path="/nonexistent/profile.json")
