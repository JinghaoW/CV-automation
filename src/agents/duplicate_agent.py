"""DuplicateAgent: history-based duplicate detection wrappers."""
from __future__ import annotations

import asyncio
from typing import Dict, Optional

from src.recommendation_history import RecommendationHistory, stable_job_hash


class DuplicateAgent:
    def __init__(self, history_path: Optional[str] = None) -> None:
        self.history = RecommendationHistory(path=history_path) if history_path else RecommendationHistory()

    async def has(self, job: Dict) -> bool:
        h = stable_job_hash(job)
        return await asyncio.to_thread(self.history.has, h)

    async def mark_recommended(self, job: Dict) -> None:
        h = stable_job_hash(job)
        await asyncio.to_thread(self.history.add_recommendation, h, job)

    async def mark_viewed(self, job: Dict) -> None:
        h = stable_job_hash(job)
        await asyncio.to_thread(self.history.mark_viewed, h)

    async def mark_applied(self, job: Dict) -> None:
        h = stable_job_hash(job)
        await asyncio.to_thread(self.history.mark_applied, h)

    async def mark_dismissed(self, job: Dict) -> None:
        h = stable_job_hash(job)
        await asyncio.to_thread(self.history.mark_dismissed, h)

