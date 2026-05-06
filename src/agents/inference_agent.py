"""InferenceAgent: produce LLM evaluations for jobs given a profile."""
from __future__ import annotations

import asyncio
from typing import Dict, Any

from src.llm_client import OpenAI, validate_llm_configuration
from src.evaluate_jobs import _build_evaluation_prompt


class InferenceAgent:
    def __init__(self, llm_client: OpenAI | None = None) -> None:
        self.llm_client = llm_client or OpenAI.from_config()

    async def evaluate(self, profile: Dict[str, Any], job: Dict[str, Any]) -> Dict[str, Any]:
        """Return the LLM evaluation (raw dict) for a single job."""
        prompt = _build_evaluation_prompt(profile, job)

        def _call():
            return self.llm_client.generate_json(prompt, temperature=0.1)

        return await asyncio.to_thread(_call)

