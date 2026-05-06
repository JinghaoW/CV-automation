"""Pipeline orchestration endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status, BackgroundTasks

from src.models import (
    PipelineRunRequest,
    PipelineStatusResponse,
    RankedResults,
)
from src.api.app import create_session, get_session, update_session
from src.parse_cv import parse_cv
from src.job_search import run as search_jobs
from src.evaluate_jobs import evaluate_jobs
from src.rank_jobs import rank_jobs
from src.recommendation_history import RecommendationHistory

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


def _run_pipeline_background(session_id: str, skip_email: bool = False) -> None:
    """Execute pipeline steps in background."""
    try:
        update_session(session_id, {"status": "running"})

        # Step 1: Parse CV
        update_session(session_id, {"current_step": 1, "step_name": "Parsing CV"})
        profile = parse_cv()

        # Step 2: Search jobs
        update_session(session_id, {"current_step": 2, "step_name": "Searching jobs"})
        raw_jobs = search_jobs()

        if not raw_jobs:
            update_session(session_id, {
                "status": "completed",
                "current_step": 6,
                "results": RankedResults(all_jobs=[], total_count=0).model_dump(),
            })
            return

        # Step 3: Evaluate jobs
        update_session(session_id, {"current_step": 3, "step_name": "Evaluating jobs"})
        scored_jobs = evaluate_jobs()

        # Step 4: Rank jobs
        update_session(session_id, {"current_step": 4, "step_name": "Ranking jobs"})
        ranked = rank_jobs()

        results = RankedResults(
            all_jobs=ranked.get("all_jobs", []),
            by_country=ranked.get("by_country", {}),
            by_classification=ranked.get("by_classification", {}),
            total_count=len(ranked.get("all_jobs", [])),
        )

        # Store in session
        session_data = get_session(session_id)
        session_data["profile"] = profile
        session_data["results"] = results.model_dump()

        # Record in history
        history = RecommendationHistory()
        all_jobs = ranked.get("all_jobs", [])
        top_score = 0
        if all_jobs:
            scores = [job.get("score", 0) for job in all_jobs if isinstance(job, dict)]
            top_score = max(scores) if scores else 0

        history.record_search(
            profile_name=profile.get("name", "Unknown"),
            job_count=results.total_count,
            top_score=top_score,
            session_id=session_id,
        )

        update_session(session_id, {
            "status": "completed",
            "current_step": 6,
            "completed_at": datetime.now(tz=timezone.utc).isoformat(),
        })

    except Exception as e:
        print(f"[pipeline] Error in background task: {e}")
        update_session(session_id, {
            "status": "failed",
            "error": str(e),
        })


@router.post("/run")
async def run_pipeline(
    request: PipelineRunRequest,
    background_tasks: BackgroundTasks,
) -> dict:
    """Trigger a new pipeline run.

    Returns immediately with session_id. Poll /pipeline/{session_id}/status
    for progress and results.
    """
    session_id = create_session()

    # Start pipeline in background
    background_tasks.add_task(
        _run_pipeline_background,
        session_id,
        skip_email=request.skip_email,
    )

    return {
        "session_id": session_id,
        "message": "Pipeline started",
        "status_url": f"/pipeline/{session_id}/status",
    }


@router.get("/status/{session_id}")
async def get_pipeline_status(session_id: str) -> PipelineStatusResponse:
    """Get current status of a pipeline run."""
    try:
        session = get_session(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )

    status_map = {
        0: "Initializing",
        1: "Parsing CV",
        2: "Searching jobs",
        3: "Evaluating jobs",
        4: "Ranking jobs",
        5: "Building report",
        6: "Complete",
    }

    current_step = session.get("current_step", 0)
    step_name = status_map.get(current_step, "Unknown")

    # Calculate progress
    progress = int((current_step / 6) * 100) if session.get("status") == "running" else (
        100 if session.get("status") == "completed" else 0
    )

    # Calculate elapsed time
    elapsed = 0
    if "created_at" in session:
        created = datetime.fromisoformat(session["created_at"].replace("Z", "+00:00"))
        elapsed = (datetime.now(tz=timezone.utc) - created).total_seconds()

    return PipelineStatusResponse(
        session_id=session_id,
        status=session.get("status", "pending"),
        current_step=current_step,
        step_name=step_name,
        progress_percent=progress,
        elapsed_seconds=elapsed,
        error=session.get("error"),
        results=session.get("results"),
    )


@router.get("/{session_id}/report")
async def get_pipeline_report(session_id: str) -> dict:
    """Get detailed report from a completed pipeline run."""
    try:
        session = get_session(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )

    if session.get("status") != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pipeline has not completed yet"
        )

    return {
        "session_id": session_id,
        "profile": session.get("profile"),
        "results": session.get("results"),
        "completed_at": session.get("completed_at"),
    }

