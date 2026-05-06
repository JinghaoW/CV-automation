"""Entry point for running the API server.

Usage:
    python -m src.api.server
    # or
    uvicorn src.api.server:app --reload --port 8000
"""

from src.api.app import create_app

app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )

