"""Unit tests for src/evaluate_jobs.py."""

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from src.evaluate_jobs import _build_evaluation_prompt, evaluate_job, evaluate_jobs


# ---------------------------------------------------------------------------
# _build_evaluation_prompt
# ---------------------------------------------------------------------------

def test_build_evaluation_prompt_contains_skills():
    profile = {"skills": ["Python", "Machine Learning"], "summary": "Experienced ML engineer"}
    job = {"title": "Data Scientist", "company": "ACME", "description": "We need ML skills"}
    prompt = _build_evaluation_prompt(profile, job)
    assert "Python" in prompt
    assert "Machine Learning" in prompt
    assert "Data Scientist" in prompt
    assert "ACME" in prompt
    assert "We need ML skills" in prompt


def test_build_evaluation_prompt_truncates_description():
    profile = {"skills": ["Python"], "summary": ""}
    long_description = "x" * 5000
    job = {"title": "Job", "company": "Co", "description": long_description}
    prompt = _build_evaluation_prompt(profile, job)
    # Description is truncated to _MAX_DESC_CHARS (3000)
    assert long_description not in prompt
    assert "x" * 3000 in prompt


def test_build_evaluation_prompt_empty_profile():
    profile = {}
    job = {"title": "Analyst", "company": "Firm", "description": "Finance role"}
    prompt = _build_evaluation_prompt(profile, job)
    assert "Analyst" in prompt
    assert isinstance(prompt, str)


# ---------------------------------------------------------------------------
# evaluate_job – mocking OpenAI client
# ---------------------------------------------------------------------------

def _make_mock_client(content: str) -> MagicMock:
    client = MagicMock()
    choice = MagicMock()
    choice.message.content = content
    client.chat.completions.create.return_value.choices = [choice]
    return client


def test_evaluate_job_success():
    profile = {"skills": ["Python"], "summary": "Developer"}
    job = {"title": "Engineer", "company": "Co", "description": "Python job", "url": "https://co.com"}
    llm_response = json.dumps({"score": 8, "classification": "industry", "reasoning": "Good match"})

    client = _make_mock_client(llm_response)
    result = evaluate_job(profile, job, client)

    assert result["score"] == 8
    assert result["classification"] == "industry"
    assert result["reasoning"] == "Good match"
    assert result["title"] == "Engineer"


def test_evaluate_job_none_content():
    """LLM returning None content should produce score 0."""
    profile = {"skills": ["Python"], "summary": "Developer"}
    job = {"title": "Engineer", "company": "Co", "description": "desc", "url": ""}
    client = _make_mock_client(None)

    result = evaluate_job(profile, job, client)
    assert result["score"] == 0
    assert result["classification"] == "unknown"


def test_evaluate_job_invalid_json():
    """LLM returning invalid JSON should produce score 0."""
    profile = {"skills": ["Go"], "summary": "Engineer"}
    job = {"title": "Backend", "company": "X", "description": "desc", "url": ""}
    client = _make_mock_client("this is not json")

    result = evaluate_job(profile, job, client)
    assert result["score"] == 0


# ---------------------------------------------------------------------------
# evaluate_jobs – integration with file I/O
# ---------------------------------------------------------------------------

@patch("src.evaluate_jobs.config")
@patch("src.evaluate_jobs.OpenAI")
def test_evaluate_jobs_saves_scored(mock_openai_cls, mock_config):
    mock_config.OPENAI_API_KEY = "test-key"

    llm_content = json.dumps({"score": 7, "classification": "research", "reasoning": "Nice"})
    mock_client = _make_mock_client(llm_content)
    mock_openai_cls.return_value = mock_client

    profile = {"skills": ["Python"], "summary": "Dev"}
    jobs = [{"title": "Researcher", "company": "Uni", "description": "AI research", "url": ""}]

    with tempfile.TemporaryDirectory() as tmpdir:
        profile_path = os.path.join(tmpdir, "profile.json")
        jobs_raw_path = os.path.join(tmpdir, "jobs_raw.json")
        jobs_scored_path = os.path.join(tmpdir, "jobs_scored.json")

        with open(profile_path, "w") as fh:
            json.dump(profile, fh)
        with open(jobs_raw_path, "w") as fh:
            json.dump(jobs, fh)

        with patch("src.evaluate_jobs.JOBS_SCORED_PATH", jobs_scored_path):
            result = evaluate_jobs(profile_path=profile_path, jobs_raw_path=jobs_raw_path)

        assert len(result) == 1
        assert result[0]["score"] == 7
        assert os.path.exists(jobs_scored_path)


@patch("src.evaluate_jobs.config")
def test_evaluate_jobs_no_api_key(mock_config):
    mock_config.OPENAI_API_KEY = ""
    with pytest.raises(EnvironmentError, match="OPENAI_API_KEY"):
        evaluate_jobs()


def test_evaluate_jobs_missing_file():
    with patch("src.evaluate_jobs.config") as mock_config:
        mock_config.OPENAI_API_KEY = "key"
        with pytest.raises(FileNotFoundError):
            evaluate_jobs(
                profile_path="/nonexistent/profile.json",
                jobs_raw_path="/nonexistent/jobs_raw.json",
            )
