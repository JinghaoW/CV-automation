"""Job results and filtering endpoints."""

from typing import Optional

from fastapi import APIRouter, HTTPException, status, Query

from src.models import Job
from src.api.app import get_session

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{session_id}")
async def get_session_jobs(
    session_id: str,
    min_score: int = Query(1, ge=1, le=10),
    max_score: int = Query(10, ge=1, le=10),
    country: Optional[str] = Query(None),
    classification: Optional[str] = Query(None),
    sort_by: str = Query("score", regex="^(score|title|company|country)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
) -> dict:
    """Get jobs from a session with optional filtering.

    Args:
        session_id: Session ID from pipeline run
        min_score: Minimum job score (1-10)
        max_score: Maximum job score (1-10)
        country: Filter by country
        classification: Filter by classification (research/industry)
        sort_by: Sort field
        sort_order: Sort direction (asc/desc)

    Returns:
        Filtered and sorted job list
    """
    try:
        session = get_session(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )

    results = session.get("results")
    if not results:
        return {"jobs": [], "total": 0}

    jobs_data = results.get("all_jobs", [])

    # Filter
    filtered = [
        Job(**job) if isinstance(job, dict) else job
        for job in jobs_data
        if job.get("score", 0) >= min_score
        and job.get("score", 0) <= max_score
        and (not country or job.get("country", "").lower() == country.lower())
        and (not classification or job.get("classification", "") == classification)
    ]

    # Sort
    reverse = sort_order == "desc"
    if sort_by == "score":
        filtered.sort(key=lambda j: j.get("score", 0), reverse=reverse)
    elif sort_by == "title":
        filtered.sort(key=lambda j: j.get("title", ""), reverse=reverse)
    elif sort_by == "company":
        filtered.sort(key=lambda j: j.get("company", ""), reverse=reverse)
    elif sort_by == "country":
        filtered.sort(key=lambda j: j.get("country", ""), reverse=reverse)

    return {
        "jobs": filtered,
        "total": len(filtered),
        "filters": {
            "min_score": min_score,
            "max_score": max_score,
            "country": country,
            "classification": classification,
        },
    }


@router.get("/{session_id}/{job_index}")
async def get_job_detail(session_id: str, job_index: int) -> dict:
    """Get detailed information about a specific job."""
    try:
        session = get_session(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )

    results = session.get("results")
    if not results or job_index >= len(results.get("all_jobs", [])):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    job = results["all_jobs"][job_index]
    return {
        "job": job,
        "index": job_index,
        "total": len(results.get("all_jobs", [])),
        "navigation": {
            "prev": job_index - 1 if job_index > 0 else None,
            "next": job_index + 1 if job_index < len(results.get("all_jobs", [])) - 1 else None,
        },
    }


@router.post("/{session_id}/{job_index}/action")
async def job_action(
    session_id: str,
    job_index: int,
    action: str = Query(..., regex="^(view|apply|dismiss)$"),
    notes: Optional[str] = Query(None),
) -> dict:
    """Record an action on a job (view, apply, dismiss).

    This updates the search history.
    """
    try:
        session = get_session(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )

    results = session.get("results")
    if not results or job_index >= len(results.get("all_jobs", [])):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # Update job metadata
    job = results["all_jobs"][job_index]
    if action == "view":
        job["viewed"] = True
    elif action == "apply":
        job["applied"] = True
    elif action == "dismiss":
        job["dismissed"] = True

    if notes:
        job["notes"] = notes

    # Persist to history
    from src.recommendation_history import RecommendationHistory
    history = RecommendationHistory()
    history.record_action(
        session_id=session_id,
        job_id=job.get("id"),
        action=action,
    )

    return {
        "success": True,
        "action": action,
        "job": job,
    }


@router.get("/{session_id}/by-country")
async def get_jobs_by_country(session_id: str) -> dict:
    """Get jobs grouped by country."""
    try:
        session = get_session(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )

    results = session.get("results", {})
    return {
        "by_country": results.get("by_country", {}),
        "total": len(results.get("all_jobs", [])),
    }


@router.get("/{session_id}/by-classification")
async def get_jobs_by_classification(session_id: str) -> dict:
    """Get jobs grouped by classification (research/industry)."""
    try:
        session = get_session(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )

    results = session.get("results", {})
    return {
        "by_classification": results.get("by_classification", {}),
        "total": len(results.get("all_jobs", [])),
    }

