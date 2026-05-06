"""Unit tests for src/recommendation_history.py."""

import os
import tempfile

from src.recommendation_history import RecommendationHistory, stable_job_hash


# ---------------------------------------------------------------------------
# stable_job_hash
# ---------------------------------------------------------------------------


def test_stable_job_hash_is_deterministic():
    job = {"title": "Engineer", "company": "Co", "url": "https://co.com/job/1"}
    assert stable_job_hash(job) == stable_job_hash(job)


def test_stable_job_hash_differs_for_different_jobs():
    a = {"title": "A", "company": "Co", "url": "https://a.com"}
    b = {"title": "B", "company": "Co", "url": "https://b.com"}
    assert stable_job_hash(a) != stable_job_hash(b)


def test_stable_job_hash_returns_16_char_hex():
    job = {"title": "SWE", "company": "X", "url": "https://x.com"}
    h = stable_job_hash(job)
    assert len(h) == 16
    int(h, 16)  # should not raise — confirms it's valid hex


# ---------------------------------------------------------------------------
# RecommendationHistory
# ---------------------------------------------------------------------------


def _make_job(suffix: str = "") -> dict:
    return {
        "title": f"Job {suffix}",
        "company": "Corp",
        "url": f"https://corp.com/{suffix}",
    }


def test_history_add_and_has():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "history.json")
        history = RecommendationHistory(path)
        job = _make_job("1")
        h = stable_job_hash(job)

        assert not history.has(h)
        history.add_recommendation(h, job)
        assert history.has(h)


def test_history_add_is_idempotent():
    """Adding the same hash twice should not create duplicate entries."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "history.json")
        history = RecommendationHistory(path)
        job = _make_job("2")
        h = stable_job_hash(job)

        history.add_recommendation(h, job)
        history.add_recommendation(h, job)  # second call is a no-op
        assert len(history.all_entries()) == 1


def test_history_update_status():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "history.json")
        history = RecommendationHistory(path)
        job = _make_job("3")
        h = stable_job_hash(job)
        history.add_recommendation(h, job)

        assert history.update_status(h, "viewed") is True
        assert history.all_entries()[0]["status"] == "viewed"


def test_history_update_status_unknown_hash_returns_false():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "history.json")
        history = RecommendationHistory(path)
        assert history.update_status("nonexistent", "applied") is False


def test_history_mark_helpers():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "history.json")
        history = RecommendationHistory(path)
        job = _make_job("4")
        h = stable_job_hash(job)
        history.add_recommendation(h, job)

        assert history.mark_viewed(h) is True
        assert history.mark_applied(h) is True
        assert history.mark_dismissed(h) is True
        assert history.all_entries()[0]["status"] == "dismissed"


def test_history_persists_across_instances():
    """A new instance loading the same file should see existing entries."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "history.json")
        job = _make_job("5")
        key = stable_job_hash(job)

        h1 = RecommendationHistory(path)
        h1.add_recommendation(key, job)

        h2 = RecommendationHistory(path)
        assert h2.has(key)
        assert h2.all_entries()[0]["status"] == "recommended"
