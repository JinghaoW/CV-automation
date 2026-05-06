"""Typed Pydantic models for frontend data contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class Profile(BaseModel):
    """Candidate profile extracted from a CV."""

    name: str = ""
    skills: list[str] = Field(default_factory=list)
    experience_years: float = 0.0
    education: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    summary: str = ""


class Job(BaseModel):
    """Raw job listing fetched from a job source."""

    title: str = ""
    company: str = ""
    location: str = ""
    country: str = ""
    description: str = ""
    url: str = ""
    source: str = ""
    category: str = ""


class ScoredJob(Job):
    """Job listing enriched with LLM evaluation scores."""

    score: int = 0
    classification: str = "unknown"
    reasoning: str = ""


class UploadResponse(BaseModel):
    """Response returned after a CV file upload."""

    message: str
    filename: str
    cv_path: str


class RunRecord(BaseModel):
    """Record of a single pipeline run."""

    run_id: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    jobs_found: int = 0
    jobs_scored: int = 0
    error: Optional[str] = None


class SearchHistoryEntry(BaseModel):
    """Summary of a past pipeline run shown in the search history."""

    run_id: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    status: str
    jobs_found: int = 0
    jobs_scored: int = 0
