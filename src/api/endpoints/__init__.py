"""API endpoints package."""

from .upload import router as upload_router
from .pipeline import router as pipeline_router
from .results import router as results_router
from .history import router as history_router
from .config import router as config_router

__all__ = [
    "upload_router",
    "pipeline_router",
    "results_router",
    "history_router",
    "config_router",
]

