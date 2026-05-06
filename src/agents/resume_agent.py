"""ResumeAgent: parse CVs into structured Profile objects asynchronously."""
from __future__ import annotations

import asyncio
from dataclasses import asdict
from typing import Optional

from src.parse_cv import extract_text_from_pdf, parse_text_to_profile, Profile
from src.llm_client import OpenAI


class ResumeAgent:
    """Agent that handles resume ingestion and parsing.

    Methods are async-friendly and use threads to call blocking PDF/LLM code.
    """

    def __init__(self, llm_client: Optional[OpenAI] = None) -> None:
        self.llm_client = llm_client or OpenAI.from_config()

    async def parse_pdf(self, path: str) -> Profile:
        # extract text (blocking) in thread
        cv_text = await asyncio.to_thread(extract_text_from_pdf, path)
        profile = await asyncio.to_thread(parse_text_to_profile, cv_text, self.llm_client)
        return profile

    async def parse_pdf_and_dict(self, path: str) -> dict:
        profile = await self.parse_pdf(path)
        return profile.to_dict()

