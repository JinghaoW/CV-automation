"""Unit tests for src/parse_cv.py."""

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from src.parse_cv import extract_skills_with_llm, parse_cv


# ---------------------------------------------------------------------------
# extract_skills_with_llm
# ---------------------------------------------------------------------------

def _make_mock_client(content) -> MagicMock:
    client = MagicMock()
    client.generate_json.return_value = content
    return client


def test_extract_skills_valid_json():
    profile_data = {
        "name": "Jane Doe",
        "skills": ["Python", "Machine Learning"],
        "experience_years": 5,
        "education": ["PhD Computer Science"],
        "languages": ["English"],
        "summary": "Experienced researcher.",
    }
    client = _make_mock_client(profile_data)
    result = extract_skills_with_llm("some cv text", client)
    assert result["name"] == "Jane Doe"
    assert "Python" in result["skills"]
    assert result["experience_years"] == 5


def test_extract_skills_none_content():
    """None response content should raise ValueError."""
    client = MagicMock()
    client.generate_json.side_effect = ValueError("LLM returned no content (content was None)")
    with pytest.raises(ValueError, match="None"):
        extract_skills_with_llm("some cv text", client)


def test_extract_skills_invalid_json():
    """Invalid JSON from the LLM should raise ValueError."""
    client = MagicMock()
    client.generate_json.side_effect = ValueError("LLM returned invalid JSON: not json at all")
    with pytest.raises(ValueError, match="invalid JSON"):
        extract_skills_with_llm("some cv text", client)


# ---------------------------------------------------------------------------
# parse_cv – integration
# ---------------------------------------------------------------------------

@patch("src.parse_cv.config")
@patch("src.parse_cv.OpenAI")
@patch("src.parse_cv.extract_text_from_pdf")
def test_parse_cv_saves_profile(mock_extract_text, mock_openai_cls, mock_config):
    mock_config.OPENAI_API_KEY = "test-key"
    mock_config.CV_PATH = "cv/CV.pdf"
    mock_extract_text.return_value = "Jane Doe, Python developer"

    profile_data = {
        "name": "Jane Doe",
        "skills": ["Python"],
        "experience_years": 3,
        "education": ["BSc"],
        "languages": ["English"],
        "summary": "Python dev.",
    }
    mock_client = _make_mock_client(profile_data)
    mock_openai_cls.return_value = mock_client

    with tempfile.TemporaryDirectory() as tmpdir:
        profile_path = os.path.join(tmpdir, "profile.json")
        with patch("src.parse_cv.PROFILE_PATH", profile_path):
            # Also patch os.makedirs so it writes to tmpdir
            result = parse_cv(cv_path="cv/CV.pdf")

        assert result["name"] == "Jane Doe"
        assert os.path.exists(profile_path)
        with open(profile_path) as fh:
            saved = json.load(fh)
        assert saved["name"] == "Jane Doe"


@patch("src.parse_cv.config")
def test_parse_cv_no_api_key(mock_config):
    mock_config.OPENAI_API_KEY = ""
    with pytest.raises(EnvironmentError, match="OPENAI_API_KEY"):
        parse_cv(cv_path="cv/CV.pdf")


@patch("src.parse_cv.config")
@patch("src.parse_cv.OpenAI")
def test_parse_cv_missing_pdf(mock_openai_cls, mock_config):
    mock_config.OPENAI_API_KEY = "test-key"
    mock_openai_cls.return_value = MagicMock()

    with pytest.raises(FileNotFoundError):
        parse_cv(cv_path="/nonexistent/CV.pdf")
