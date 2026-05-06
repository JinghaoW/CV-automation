"""Recommendation history and duplicate detection.

Provides stable job hashing and simple file-backed history tracking for
recommendations: recommended, viewed, applied, dismissed. The history is kept
in JSON at data/recommendation_history.json and is intentionally simple so it
can be ported to Postgres/Redis later.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, Optional

HISTORY_PATH = os.path.join("data", "recommendation_history.json")
SEARCH_HISTORY_PATH = os.path.join("data", "search_history.json")
ACTIONS_PATH = os.path.join("data", "user_actions.json")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_job_hash(job: Dict[str, Any]) -> str:
    """Create a stable hash for a job listing.

    Prefer URL-based hashing when available; otherwise canonicalize title +
    company + location + description. This function is deterministic and
    suitable for deduplication across runs.
    """
    url = (job.get("url") or "").strip()
    if url:
        base = url.lower()
    else:
        components = [
            str(job.get("title", "")),
            str(job.get("company", "")),
            str(job.get("location", "")),
            str(job.get("description", ""))[:2000],
        ]
        base = "|".join(c.strip().lower() for c in components if c)
    h = hashlib.sha256(base.encode("utf-8")).hexdigest()
    return h


@dataclass
class HistoryRecord:
    job_hash: str
    first_seen: str
    last_seen: str
    times_recommended: int
    viewed_at: Optional[str] = None
    applied_at: Optional[str] = None
    dismissed_at: Optional[str] = None
    job_snapshot: Optional[Dict[str, Any]] = None

    def touch_recommended(self, job: Optional[Dict[str, Any]] = None) -> None:
        now = _now_iso()
        if not self.first_seen:
            self.first_seen = now
        self.last_seen = now
        self.times_recommended = (self.times_recommended or 0) + 1
        if job is not None:
            self.job_snapshot = job


class RecommendationHistory:
    def __init__(self, path: str = HISTORY_PATH) -> None:
        self.path = path
        self._data: Dict[str, HistoryRecord] = {}
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.path):
            self._data = {}
            return
        try:
            with open(self.path, encoding="utf-8") as fh:
                raw = json.load(fh)
            out: Dict[str, HistoryRecord] = {}
            for k, v in raw.items():
                out[k] = HistoryRecord(
                    job_hash=k,
                    first_seen=v.get("first_seen", ""),
                    last_seen=v.get("last_seen", ""),
                    times_recommended=v.get("times_recommended", 0),
                    viewed_at=v.get("viewed_at"),
                    applied_at=v.get("applied_at"),
                    dismissed_at=v.get("dismissed_at"),
                    job_snapshot=v.get("job_snapshot"),
                )
            self._data = out
        except Exception:
            # Corrupt file: treat as empty (fail-safe)
            self._data = {}

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.path) or "data", exist_ok=True)
        out = {k: asdict(v) for k, v in self._data.items()}
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=2, ensure_ascii=False)

    def has(self, job_hash: str) -> bool:
        return job_hash in self._data

    def add_recommendation(self, job_hash: str, job: Optional[Dict[str, Any]] = None) -> None:
        rec = self._data.get(job_hash)
        if rec is None:
            rec = HistoryRecord(
                job_hash=job_hash,
                first_seen=_now_iso(),
                last_seen=_now_iso(),
                times_recommended=0,
                job_snapshot=job,
            )
            self._data[job_hash] = rec
        rec.touch_recommended(job)
        self._save()

    def mark_viewed(self, job_hash: str) -> None:
        rec = self._data.get(job_hash)
        if rec is None:
            return
        rec.viewed_at = _now_iso()
        self._save()

    def mark_applied(self, job_hash: str) -> None:
        rec = self._data.get(job_hash)
        if rec is None:
            return
        rec.applied_at = _now_iso()
        self._save()

    def mark_dismissed(self, job_hash: str) -> None:
        rec = self._data.get(job_hash)
        if rec is None:
            return
        rec.dismissed_at = _now_iso()
        self._save()

    def get_record(self, job_hash: str) -> Optional[HistoryRecord]:
        return self._data.get(job_hash)

    def all_records(self) -> Dict[str, HistoryRecord]:
        return dict(self._data)

    # =========================================================================
    # API-friendly methods for search session tracking
    # =========================================================================

    def record_search(
        self,
        profile_name: str = "",
        job_count: int = 0,
        top_score: int = 0,
        session_id: Optional[str] = None,
        country_filter: str = "",
    ) -> None:
        """Record a search session."""
        os.makedirs(os.path.dirname(SEARCH_HISTORY_PATH) or "data", exist_ok=True)

        search_records = []
        if os.path.exists(SEARCH_HISTORY_PATH):
            try:
                with open(SEARCH_HISTORY_PATH, encoding="utf-8") as fh:
                    search_records = json.load(fh)
            except Exception:
                search_records = []

        search_records.append({
            "session_id": session_id or "",
            "profile_name": profile_name,
            "job_count": job_count,
            "top_score": top_score,
            "searched_at": _now_iso(),
            "completed_at": _now_iso(),
            "country_filter": country_filter,
        })

        with open(SEARCH_HISTORY_PATH, "w", encoding="utf-8") as fh:
            json.dump(search_records, fh, indent=2, ensure_ascii=False)

    def record_action(
        self,
        session_id: str = "",
        job_id: str = "",
        action: str = "",
    ) -> None:
        """Record a user action on a job."""
        os.makedirs(os.path.dirname(ACTIONS_PATH) or "data", exist_ok=True)

        actions = []
        if os.path.exists(ACTIONS_PATH):
            try:
                with open(ACTIONS_PATH, encoding="utf-8") as fh:
                    actions = json.load(fh)
            except Exception:
                actions = []

        actions.append({
            "session_id": session_id,
            "job_id": job_id,
            "action": action,
            "timestamp": _now_iso(),
        })

        with open(ACTIONS_PATH, "w", encoding="utf-8") as fh:
            json.dump(actions, fh, indent=2, ensure_ascii=False)

    def get_all(self) -> list[Dict[str, Any]]:
        """Get all search history records."""
        if not os.path.exists(SEARCH_HISTORY_PATH):
            return []

        try:
            with open(SEARCH_HISTORY_PATH, encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return []

    def get_by_session(self, session_id: str) -> list[Dict[str, Any]]:
        """Get history records for a specific session."""
        all_records = self.get_all()
        return [r for r in all_records if r.get("session_id") == session_id]

    def get_actions_by_session(self, session_id: str) -> list[Dict[str, Any]]:
        """Get all user actions for a session."""
        if not os.path.exists(ACTIONS_PATH):
            return []

        try:
            with open(ACTIONS_PATH, encoding="utf-8") as fh:
                actions = json.load(fh)
            return [a for a in actions if a.get("session_id") == session_id]
        except Exception:
            return []

    def delete_session(self, session_id: str) -> None:
        """Delete all history for a session."""
        # Delete from search history
        if os.path.exists(SEARCH_HISTORY_PATH):
            try:
                with open(SEARCH_HISTORY_PATH, encoding="utf-8") as fh:
                    records = json.load(fh)
                records = [r for r in records if r.get("session_id") != session_id]
                with open(SEARCH_HISTORY_PATH, "w", encoding="utf-8") as fh:
                    json.dump(records, fh, indent=2, ensure_ascii=False)
            except Exception:
                pass

        # Delete from actions
        if os.path.exists(ACTIONS_PATH):
            try:
                with open(ACTIONS_PATH, encoding="utf-8") as fh:
                    actions = json.load(fh)
                actions = [a for a in actions if a.get("session_id") != session_id]
                with open(ACTIONS_PATH, "w", encoding="utf-8") as fh:
                    json.dump(actions, fh, indent=2, ensure_ascii=False)
            except Exception:
                pass


__all__ = [
    "stable_job_hash",
    "RecommendationHistory",
    "HistoryRecord",
]

