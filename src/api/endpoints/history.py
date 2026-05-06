"""Search history endpoints."""

from fastapi import APIRouter, HTTPException, status

from src.recommendation_history import RecommendationHistory

router = APIRouter(prefix="/history", tags=["history"])


@router.get("/")
async def get_history(
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """Get search history.

    Args:
        limit: Number of records to return (max 100)
        offset: Pagination offset

    Returns:
        List of search history records
    """
    limit = min(limit, 100)  # Cap at 100

    history = RecommendationHistory()
    all_records = history.get_all()

    # Sort by most recent first
    sorted_records = sorted(
        all_records,
        key=lambda r: r.get("searched_at", ""),
        reverse=True
    )

    paginated = sorted_records[offset:offset + limit]

    return {
        "records": paginated,
        "total": len(all_records),
        "limit": limit,
        "offset": offset,
    }


@router.get("/{session_id}")
async def get_session_history(session_id: str) -> dict:
    """Get history for a specific session."""
    history = RecommendationHistory()
    session_records = history.get_by_session(session_id)

    if not session_records:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No history found for session {session_id}"
        )

    return {
        "session_id": session_id,
        "records": session_records,
        "total": len(session_records),
    }


@router.get("/{session_id}/actions")
async def get_session_actions(session_id: str) -> dict:
    """Get all user actions (viewed, applied, dismissed) for a session."""
    history = RecommendationHistory()
    actions = history.get_actions_by_session(session_id)

    # Group by action type
    grouped = {
        "viewed": [],
        "applied": [],
        "dismissed": [],
    }

    for action in actions:
        action_type = action.get("action")
        if action_type in grouped:
            grouped[action_type].append(action)

    return {
        "session_id": session_id,
        "actions": grouped,
        "total": len(actions),
    }


@router.post("/{session_id}/stats")
async def get_session_stats(session_id: str) -> dict:
    """Get statistics for a session."""
    history = RecommendationHistory()
    actions = history.get_actions_by_session(session_id)

    stats = {
        "viewed_count": len([a for a in actions if a.get("action") == "viewed"]),
        "applied_count": len([a for a in actions if a.get("action") == "applied"]),
        "dismissed_count": len([a for a in actions if a.get("action") == "dismissed"]),
        "engagement_rate": 0.0,
    }

    # You may calculate actual stats based on actual job counts if needed

    return {
        "session_id": session_id,
        "stats": stats,
    }


@router.delete("/{session_id}")
async def delete_session_history(session_id: str) -> dict:
    """Delete all history for a session."""
    history = RecommendationHistory()
    history.delete_session(session_id)

    return {
        "message": f"Deleted history for session {session_id}",
        "session_id": session_id,
    }


