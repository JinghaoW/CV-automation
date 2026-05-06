"""Configuration management endpoints."""

from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

import config

router = APIRouter(prefix="/config", tags=["config"])


class ConfigUpdateRequest(BaseModel):
    """Request to update configuration."""
    country_filter: Optional[str] = None
    email_subject: Optional[str] = None
    csv_path: Optional[str] = None


@router.get("/")
async def get_config() -> dict:
    """Get current configuration (public settings only).

    Returns only non-sensitive configuration values.
    """
    return {
        "cv_path": config.CV_PATH,
        "country": config.COUNTRY,
        "email_subject": config.EMAIL_SUBJECT,
        "llm_provider": config.LLM_PROVIDER,
        "llm_model": config.LLM_MODEL,
        "schedule_hour_utc": config.SCHEDULE_HOUR_UTC,
        "schedule_minute_utc": config.SCHEDULE_MINUTE_UTC,
    }


@router.get("/providers")
async def get_available_providers() -> dict:
    """Get list of available LLM providers."""
    return {
        "providers": ["openai", "deepseek", "gemini", "openrouter", "ollama"],
        "current": config.LLM_PROVIDER,
    }


@router.post("/")
async def update_config(request: ConfigUpdateRequest) -> dict:
    """Update configuration.

    Note: API configuration updates are temporary and don't persist.
    Permanent updates require editing config.py or environment variables.
    """
    updates = {}

    if request.country_filter is not None:
        config.COUNTRY = request.country_filter
        updates["country"] = request.country_filter

    if request.email_subject is not None:
        config.EMAIL_SUBJECT = request.email_subject
        updates["email_subject"] = request.email_subject

    if request.csv_path is not None:
        config.CV_PATH = request.csv_path
        updates["cv_path"] = request.csv_path

    return {
        "message": "Configuration updated (session only)",
        "updates": updates,
        "note": "Changes are not persisted. Edit config.py for permanent changes.",
    }


@router.get("/status")
async def get_config_status() -> dict:
    """Check configuration validation status."""
    issues = []

    # Check required settings
    if not config.OPENAI_API_KEY:
        issues.append("OPENAI_API_KEY is not set")

    if not config.GMAIL_SENDER:
        issues.append("GMAIL_SENDER is not set")

    if not config.GMAIL_APP_PASS:
        issues.append("GMAIL_APP_PASS is not set")

    if not config.GMAIL_RECIPIENT:
        issues.append("GMAIL_RECIPIENT is not set")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "can_search": len(issues) == 0,  # Only needs OpenAI key for search
        "can_email": len([i for i in issues if "GMAIL" in i or "OPENAI" in i]) == 0,
    }

