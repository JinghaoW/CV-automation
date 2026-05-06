"""Lightweight LangGraph-like orchestrator for the job recommendation workflow.

This module implements an async workflow that composes the modular agents:

ResumeAgent -> InferenceAgent -> SearchPlanningAgent -> SearchAgent ->
MatchingAgent -> RankingAgent -> DuplicateAgent -> EmailAgent

Features:
- persistent run state (data/langgraph_runs.json)
- retry support with exponential backoff
- logging
- structured graph state persisted per run
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.agents import (
    ResumeAgent,
    InferenceAgent,
    SearchPlanningAgent,
    SearchAgent,
    MatchingAgent,
    RankingAgent,
    DuplicateAgent,
    EmailAgent,
)
from src.report_builder import build_report

_LOGGER = logging.getLogger(__name__)
RUNS_PATH = os.path.join("data", "langgraph_runs.json")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _persist_run(run_id: str, state: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(RUNS_PATH) or "data", exist_ok=True)
    data = {}
    if os.path.exists(RUNS_PATH):
        try:
            with open(RUNS_PATH, encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception:
            data = {}
    data[run_id] = state
    with open(RUNS_PATH, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)


def _retry_async(max_attempts: int = 3, base_delay: float = 1.0):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as exc:
                    last_exc = exc
                    backoff = min(base_delay * (2 ** (attempt - 1)), 30)
                    _LOGGER.warning("Attempt %s failed for %s: %s; retrying in %s s", attempt, func.__name__, exc, backoff)
                    await asyncio.sleep(backoff)
            raise RuntimeError(f"{func.__name__} failed after {max_attempts} attempts") from last_exc

        return wrapper

    return decorator


@dataclass
class RunState:
    id: str
    created_at: str
    updated_at: str
    status: str
    nodes: Dict[str, Any]


class LangGraphOrchestrator:
    def __init__(self) -> None:
        self.resume_agent = ResumeAgent()
        self.inference_agent = InferenceAgent()
        self.planner = SearchPlanningAgent()
        self.search_agent = SearchAgent()
        self.matcher = MatchingAgent()
        self.ranker = RankingAgent()
        self.duplicate = DuplicateAgent()
        self.emailer = EmailAgent()

    async def run(self, cv_path: str, report_path: str = "output/report.html") -> Dict[str, Any]:
        run_id = f"run-{int(time.time())}"
        state = RunState(
            id=run_id,
            created_at=_now_iso(),
            updated_at=_now_iso(),
            status="running",
            nodes={},
        )
        _persist_run(run_id, asdict(state))

        try:
            # Resume parsing
            state.nodes["resume"] = {"status": "running"}
            profile = await self.resume_agent.parse_pdf_and_dict(cv_path)
            state.nodes["resume"] = {"status": "done", "result": profile}
            state.updated_at = _now_iso()
            _persist_run(run_id, asdict(state))

            # Planning
            state.nodes["plan"] = {"status": "running"}
            plan = self.planner.plan_keywords(profile)
            state.nodes["plan"] = {"status": "done", "result": {"keywords": plan.keywords}}
            state.updated_at = _now_iso()
            _persist_run(run_id, asdict(state))

            # Search
            state.nodes["search"] = {"status": "running"}
            jobs = await self.search_agent.search(profile)
            state.nodes["search"] = {"status": "done", "result": {"count": len(jobs)}}
            state.updated_at = _now_iso()
            _persist_run(run_id, asdict(state))

            if not jobs:
                state.status = "done"
                state.updated_at = _now_iso()
                _persist_run(run_id, asdict(state))
                return asdict(state)

            # Inference + matching in parallel with bounded concurrency
            state.nodes["inference_matching"] = {"status": "running"}

            sem = asyncio.Semaphore(6)

            async def _process_job(job):
                async with sem:
                    try:
                        eval_raw = await self.inference_agent.evaluate(profile, job)
                    except Exception as exc:
                        _LOGGER.exception("Inference failed for job %s: %s", job.get("title"), exc)
                        eval_raw = {"score": 0, "classification": "unknown", "reasoning": str(exc)}
                    scored = await self.matcher.evaluate_job(profile, job, eval_raw)
                    return scored

            scored_jobs = await asyncio.gather(*[_process_job(j) for j in jobs])
            state.nodes["inference_matching"] = {"status": "done", "result": {"count": len(scored_jobs)}}
            state.updated_at = _now_iso()
            _persist_run(run_id, asdict(state))

            # Ranking
            state.nodes["ranking"] = {"status": "running"}
            ranking = await self.ranker.rank(scored_jobs)
            state.nodes["ranking"] = {"status": "done", "result": {"all_jobs": len(ranking.get("all_jobs", []))}}
            state.updated_at = _now_iso()
            _persist_run(run_id, asdict(state))

            # Duplicate detection and mark recommended
            state.nodes["duplicates"] = {"status": "running"}
            delivered = []
            for job in ranking.get("all_jobs", []):
                if not await self.duplicate.has(job):
                    await self.duplicate.mark_recommended(job)
                    delivered.append(job)
            state.nodes["duplicates"] = {"status": "done", "result": {"delivered": len(delivered)}}
            state.updated_at = _now_iso()
            _persist_run(run_id, asdict(state))

            # Save scored jobs and build report synchronously in thread
            scored_path = os.path.join("data", "jobs_scored.json")
            os.makedirs("data", exist_ok=True)
            with open(scored_path, "w", encoding="utf-8") as fh:
                json.dump(scored_jobs, fh, indent=2, ensure_ascii=False)

            state.nodes["report"] = {"status": "running"}
            await asyncio.to_thread(build_report, jobs_scored_path=scored_path, report_path=report_path)
            state.nodes["report"] = {"status": "done", "result": {"report_path": report_path}}
            state.updated_at = _now_iso()
            _persist_run(run_id, asdict(state))

            # Email send (best-effort)
            state.nodes["email"] = {"status": "running"}
            try:
                await self.emailer.send_report(report_path)
                state.nodes["email"] = {"status": "done"}
            except Exception as exc:
                _LOGGER.exception("Email send failed: %s", exc)
                state.nodes["email"] = {"status": "failed", "error": str(exc)}
            state.updated_at = _now_iso()
            state.status = "done"
            _persist_run(run_id, asdict(state))
            return asdict(state)

        except Exception as exc:
            _LOGGER.exception("Workflow run failed: %s", exc)
            state.status = "failed"
            state.nodes["error"] = str(exc)
            state.updated_at = _now_iso()
            _persist_run(run_id, asdict(state))
            raise

