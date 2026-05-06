"""EmailAgent: async wrapper around email sending logic."""
from __future__ import annotations

import asyncio
from typing import Optional

from src.email_sender import send_email


class EmailAgent:
    async def send_report(self, report_path: str, subject: Optional[str] = None) -> None:
        # send_email is blocking; run in thread
        await asyncio.to_thread(send_email, report_path, subject)

