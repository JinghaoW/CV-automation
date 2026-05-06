"""FastAPI application for CV-automation pipeline.

Provides REST API for:
- CV uploads
- Pipeline orchestration (async with polling)
- Job result browsing with filtering
- Search history tracking
- Configuration management
"""

import os
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from src.models import ErrorResponse


# Session storage (in-memory for dev, Redis in prod)
_sessions: dict[str, Any] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifecycle."""
    # Startup
    print("[API] CV-automation API server starting...")
    yield
    # Shutdown
    print("[API] Shutting down...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(
        title="CV-automation API",
        description="REST API for automated job search pipeline",
        version="1.0.0",
        lifespan=lifespan,
    )

    # -----------------------------------------------------------------------
    # CORS configuration
    # -----------------------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # -----------------------------------------------------------------------
    # Register endpoints
    # -----------------------------------------------------------------------
    from src.api.endpoints import (
        upload_router,
        pipeline_router,
        results_router,
        history_router,
        config_router,
    )

    app.include_router(upload_router)
    app.include_router(pipeline_router)
    app.include_router(results_router)
    app.include_router(history_router)
    app.include_router(config_router)

    # -----------------------------------------------------------------------
    # Exception handlers
    # -----------------------------------------------------------------------

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc):
        return {
            "error": exc.detail,
            "error_code": "HTTP_ERROR",
        }

    @app.exception_handler(ValueError)
    async def value_error_handler(request, exc):
        return {
            "error": str(exc),
            "error_code": "VALIDATION_ERROR",
        }

    @app.exception_handler(Exception)
    async def general_exception_handler(request, exc):
        print(f"[API] Unhandled exception: {exc}", file=__import__("sys").stderr)
        return {
            "error": "Internal server error",
            "detail": str(exc) if os.environ.get("DEBUG") else "",
            "error_code": "INTERNAL_ERROR",
        }

    # -----------------------------------------------------------------------
    # Health check
    # -----------------------------------------------------------------------

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy"}

    # -----------------------------------------------------------------------
    # Sessions management
    # -----------------------------------------------------------------------

    @app.get("/sessions/{session_id}")
    async def get_session(session_id: str):
        """Get session details."""
        if session_id not in _sessions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )
        return _sessions[session_id]

    # -----------------------------------------------------------------------
    # Static files (frontend)
    # -----------------------------------------------------------------------

    frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
    if os.path.isdir(frontend_dir):
        @app.get("/")
        async def serve_frontend_root():
            """Serve frontend index.html."""
            index_path = os.path.join(frontend_dir, "index.html")
            if os.path.isfile(index_path):
                return FileResponse(index_path)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Frontend not available"
            )

        try:
            app.mount("/static", StaticFiles(directory=frontend_dir), name="static")
        except Exception as e:
            print(f"[API] Could not mount static files: {e}")

    return app


# Store sessions globally
def get_session(session_id: str) -> dict:
    """Get a session by ID."""
    if session_id not in _sessions:
        raise ValueError(f"Session {session_id} not found")
    return _sessions[session_id]


def create_session() -> str:
    """Create a new session and return its ID."""
    session_id = str(uuid.uuid4())[:8]
    _sessions[session_id] = {
        "session_id": session_id,
        "status": "init",
        "current_step": 0,
        "created_at": __import__("datetime").datetime.utcnow().isoformat(),
    }
    return session_id


def update_session(session_id: str, updates: dict) -> None:
    """Update session state."""
    if session_id not in _sessions:
        raise ValueError(f"Session {session_id} not found")
    _sessions[session_id].update(updates)


def delete_session(session_id: str) -> None:
    """Delete a session."""
    if session_id in _sessions:
        del _sessions[session_id]


# Export for use
app = create_app()

