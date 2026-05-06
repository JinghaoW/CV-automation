from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from src.tasks.celery_app import app
from src.langgraph_workflow import LangGraphOrchestrator
import config

_LOGGER = logging.getLogger(__name__)

orchestrator = LangGraphOrchestrator()


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def run_daily_workflow(self) -> dict:
    """Celery task that runs the LangGraph orchestration.

    Uses asyncio.run to execute the async orchestrator.
    Retries are handled by Celery's retry mechanism.
    """
    try:
        result = asyncio.run(orchestrator.run(config.CV_PATH, report_path=os.path.join("output", "report.html")))
        _LOGGER.info("Daily workflow completed: %s", result.get("id"))
        return result
    except Exception as exc:
        _LOGGER.exception("Daily workflow failed: %s", exc)
        try:
            raise self.retry(exc=exc)
        except Exception:
            raise

