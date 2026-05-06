"""MatchingAgent: exposes the matching engine asynchronously."""
from __future__ import annotations

import asyncio
from typing import Dict, List, Optional

from src.matching import evaluate_and_enrich_job
from src.llm_client import OpenAI


class MatchingAgent:
    def __init__(self, llm_client: Optional[OpenAI] = None) -> None:
        self.llm_client = llm_client

    async def evaluate_job(self, profile: Dict, job: Dict, llm_evaluation: Optional[Dict] = None, weights: Optional[Dict[str, float]] = None) -> Dict:
        # Run evaluate_and_enrich_job in a thread (pure CPU/sync operations)
        return await asyncio.to_thread(evaluate_and_enrich_job, profile, job, llm_evaluation, weights)

