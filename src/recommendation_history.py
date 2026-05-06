"""Recommendation history tracking with file-backed persistence."""

import hashlib
import json
import os
from datetime import datetime, timezone

HISTORY_PATH = os.path.join("data", "recommendation_history.json")


def stable_job_hash(job: dict) -> str:
    """Compute a stable 16-character hex hash for a job.

    The hash is derived from the job's title, company, and URL so that the
    same listing is always identified by the same key regardless of when it
    was fetched.
    """
    key = f"{job.get('title', '')}|{job.get('company', '')}|{job.get('url', '')}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


class RecommendationHistory:
    """File-backed store that tracks recommended jobs and their statuses.

    Each entry is keyed by the job's stable hash and holds the job data, its
    current status, and the timestamp when it was first recommended.

    Valid statuses: ``recommended``, ``viewed``, ``applied``, ``dismissed``.
    """

    def __init__(self, path: str = HISTORY_PATH) -> None:
        self._path = path
        self._data: dict[str, dict] = {}
        self._load()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if os.path.exists(self._path):
            with open(self._path, encoding="utf-8") as fh:
                self._data = json.load(fh)

    def _save(self) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(self._path)), exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as fh:
            json.dump(self._data, fh, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def has(self, job_hash: str) -> bool:
        """Return ``True`` if the job hash is already in the history."""
        return job_hash in self._data

    def add_recommendation(self, job_hash: str, job: dict) -> None:
        """Record a new recommendation.  No-op if the hash already exists."""
        if job_hash in self._data:
            return
        self._data[job_hash] = {
            "status": "recommended",
            "recommended_at": datetime.now(tz=timezone.utc).isoformat(),
            "job": job,
        }
        self._save()

    def update_status(self, job_hash: str, status: str) -> bool:
        """Update the status of an existing recommendation.

        Returns ``True`` on success, ``False`` if the hash is unknown.
        """
        if job_hash not in self._data:
            return False
        self._data[job_hash]["status"] = status
        self._save()
        return True

    def all_entries(self) -> list[dict]:
        """Return all recommendation entries as a list."""
        return list(self._data.values())

    def mark_viewed(self, job_hash: str) -> bool:
        """Mark a recommendation as viewed."""
        return self.update_status(job_hash, "viewed")

    def mark_applied(self, job_hash: str) -> bool:
        """Mark a recommendation as applied."""
        return self.update_status(job_hash, "applied")

    def mark_dismissed(self, job_hash: str) -> bool:
        """Mark a recommendation as dismissed."""
        return self.update_status(job_hash, "dismissed")
