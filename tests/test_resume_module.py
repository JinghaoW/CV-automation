"""Unit tests for the refactored resume / CV parsing helpers in src/parse_cv.py."""

import json
import os
import tempfile
from unittest.mock import MagicMock

from src.parse_cv import (
    Profile,
    parse_text_to_profile,
    extract_skills_with_llm,
    save_profile,
    save_cv_file,
)


def test_profile_roundtrip():
    data = {
        "name": "Jane Doe",
        "skills": ["Python", "ML"],
        "experience_years": 5,
        "education": ["PhD"],
        "languages": ["English"],
        "summary": "Experienced researcher.",
    }
    p = Profile.from_dict(data)
    assert p.name == "Jane Doe"
    assert "Python" in p.skills
    assert p.experience_years == 5
    assert p.to_dict() == data


def test_parse_text_to_profile_uses_client():
    mock_client = MagicMock()
    profile_data = {
        "name": "Alice",
        "skills": ["Go", "Distributed Systems"],
        "experience_years": 8,
        "education": ["MSc"],
        "languages": ["English"],
        "summary": "Senior backend engineer.",
    }
    mock_client.generate_json.return_value = profile_data

    profile = parse_text_to_profile("some text", mock_client)
    assert isinstance(profile, Profile)
    assert profile.name == "Alice"
    assert profile.experience_years == 8


def test_extract_skills_with_llm_wrapper_returns_dict():
    mock_client = MagicMock()
    profile_data = {"name": "X", "skills": ["A"]}
    mock_client.generate_json.return_value = profile_data

    result = extract_skills_with_llm("cv text", mock_client)
    assert isinstance(result, dict)
    assert result["name"] == "X"


def test_save_profile_writes_json_file():
    p = Profile(name="B", skills=["s"])
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as fh:
        path = fh.name
    try:
        save_profile(p, path)
        assert os.path.exists(path)
        with open(path, encoding="utf-8") as fh:
            saved = json.load(fh)
        assert saved["name"] == "B"
    finally:
        os.unlink(path)


def test_save_cv_file_writes_bytes():
    data = b"PDFBYTES"
    with tempfile.NamedTemporaryFile(delete=False) as fh:
        path = fh.name
    try:
        save_cv_file(data, path)
        with open(path, "rb") as fh:
            got = fh.read()
        assert got == data
    finally:
        os.unlink(path)

