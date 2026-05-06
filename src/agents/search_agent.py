"""SearchAgent: wraps job search functions with async interface."""
from __future__ import annotations

import asyncio
from typing import List, Dict, Optional

from src.job_search import search_jobs


class SearchAgent:
    """Agent to perform job searches given a profile."""

    async def search(self, profile: Dict) -> List[Dict]:
        # search_jobs is synchronous; run in thread
        return await asyncio.to_thread(search_jobs, profile)

