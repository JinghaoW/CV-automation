"""Tests for recommendation history and duplicate detection."""

import os
import tempfile

from src.recommendation_history import RecommendationHistory, stable_job_hash


def _sample_job(url=None, title="T"):
    return {"url": url or "", "title": title, "company": "C", "description": "desc", "location": "Here"}


def test_stable_hash_same_job():
    j1 = _sample_job(url="https://a.com/job/1")
    j2 = _sample_job(url="https://a.com/job/1")
    assert stable_job_hash(j1) == stable_job_hash(j2)


def test_history_add_and_query(tmp_path):
    path = tmp_path / "hist.json"
    hist = RecommendationHistory(path=str(path))
    job = _sample_job(url="https://a.com/j/1")
    h = stable_job_hash(job)
    assert not hist.has(h)
    hist.add_recommendation(h, job)
    assert hist.has(h)
    rec = hist.get_record(h)
    assert rec is not None
    assert rec.times_recommended >= 1


def test_mark_flags(tmp_path):
    path = tmp_path / "hist2.json"
    hist = RecommendationHistory(path=str(path))
    job = _sample_job(url="https://a.com/j/2")
    h = stable_job_hash(job)
    hist.add_recommendation(h, job)
    hist.mark_viewed(h)
    hist.mark_applied(h)
    hist.mark_dismissed(h)
    rec = hist.get_record(h)
    assert rec.viewed_at is not None
    assert rec.applied_at is not None
    assert rec.dismissed_at is not None

