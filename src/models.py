"""Pydantic models for frontend API contracts.

Provides typed request/response models for the REST API, decoupling
frontend from backend implementation details.
"""

from datetime import datetime, timezone
from typing import Any, Optional
from enum import Enum

from pydantic import BaseModel, Field


class JobClassification(str, Enum):
    """Job classification types."""
    RESEARCH = "research"
    INDUSTRY = "industry"
    UNKNOWN = "unknown"


class JobScore(BaseModel):
    """Basic job scoring details."""
    score: int = Field(..., ge=1, le=10, description="Job score 1-10")
    reasoning: str = Field(default="", description="LLM reasoning for score")


class Job(BaseModel):
    """Job listing with optional scores."""
    id: str = Field(default="", description="Unique job ID (hash of title + company)")
    title: str
    company: str
    location: str = Field(default="Remote", description="Job location")
    country: str = Field(default="", description="Inferred country")
    description: str = Field(default="", description="Job description text")
    url: str = Field(default="", description="Job posting URL")
    source: str = Field(default="", description="Job source (remotive, hn, etc)")
    category: str = Field(default="", description="Job category")

    # Added during evaluation
    score: int = Field(default=0, ge=0, le=10, description="LLM score 1-10")
    reasoning: str = Field(default="", description="Scoring reasoning")
    classification: JobClassification = Field(default=JobClassification.UNKNOWN)

    # Frontend metadata
    viewed: bool = Field(default=False, description="User has viewed this job")
    applied: bool = Field(default=False, description="User has applied to this job")
    dismissed: bool = Field(default=False, description="User dismissed this job")
    notes: str = Field(default="", description="User notes on the job")


class Profile(BaseModel):
    """Candidate profile extracted from CV."""
    name: str = Field(default="", description="Candidate name")
    email: str = Field(default="", description="Candidate email")
    skills: list[str] = Field(default_factory=list)
    experience: str = Field(default="", description="Years/description of experience")
    education: str = Field(default="", description="Education background")
    languages: list[str] = Field(default_factory=list)
    summary: str = Field(default="", description="Professional summary")
    cv_path: str = Field(default="", description="Path to original CV file")
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))


class RankedJob(BaseModel):
    """Job with ranking metadata."""
    job: Job
    rank: int = Field(description="Rank position (1-indexed)")


class RankedResults(BaseModel):
    """Complete ranked job results grouped by country and classification."""
    all_jobs: list[Job] = Field(default_factory=list, description="All jobs sorted by score")
    by_country: dict[str, list[Job]] = Field(default_factory=dict)
    by_classification: dict[str, list[Job]] = Field(default_factory=dict)
    total_count: int = Field(default=0)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))


class SearchSession(BaseModel):
    """Represents a single search/pipeline run."""
    session_id: str = Field(description="Unique session identifier")
    profile: Profile = Field(description="Profile used for this search")
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    completed_at: Optional[datetime] = Field(default=None)
    status: str = Field(default="pending", description="pending|running|completed|failed")
    current_step: int = Field(default=0, description="Current step 0-6")
    results: Optional[RankedResults] = Field(default=None)
    error: Optional[str] = Field(default=None)


class SearchHistoryRecord(BaseModel):
    """Single entry in search history."""
    session_id: str
    profile_name: str = Field(default="", description="Name from profile")
    job_count: int = Field(default=0, description="Total jobs found")
    top_score: int = Field(default=0, description="Highest job score")
    searched_at: datetime
    completed_at: Optional[datetime] = Field(default=None)
    country_filter: str = Field(default="", description="Country filter used")


class CVUploadResponse(BaseModel):
    """Response from CV upload endpoint."""
    success: bool
    message: str
    cv_path: str = Field(default="", description="Path to uploaded CV")
    profile: Optional[Profile] = Field(default=None, description="Extracted profile if auto-parsed")


class PipelineStatusResponse(BaseModel):
    """Current status of a pipeline run."""
    session_id: str
    status: str = Field(description="pending|running|completed|failed")
    current_step: int = Field(description="0-6, step number")
    step_name: str = Field(description="Human-readable step name")
    progress_percent: int = Field(ge=0, le=100, description="Estimated progress 0-100")
    elapsed_seconds: float = Field(ge=0)
    error: Optional[str] = Field(default=None)
    results: Optional[RankedResults] = Field(default=None)


class PipelineRunRequest(BaseModel):
    """Request to run the pipeline."""
    use_existing_cv: bool = Field(default=True, description="Use existing CV from disk")
    country_filter: str = Field(default="", description="Optional country filter")
    skip_email: bool = Field(default=False, description="Skip email send step")


class JobFilterRequest(BaseModel):
    """Request to filter/search jobs."""
    min_score: int = Field(default=1, ge=1, le=10)
    max_score: int = Field(default=10, ge=1, le=10)
    country: Optional[str] = Field(default=None, description="Filter by country")
    classification: Optional[JobClassification] = Field(default=None)
    search_text: Optional[str] = Field(default=None, description="Search in title/company/description")
    status: str = Field(default="all", description="all|applied|dismissed|viewed")


class DashboardData(BaseModel):
    """Dashboard overview data."""
    current_session: Optional[SearchSession] = Field(default=None)
    recent_searches: list[SearchHistoryRecord] = Field(default_factory=list)
    profile: Optional[Profile] = Field(default=None)
    stats: dict[str, Any] = Field(
        default_factory=dict,
        description="Stats like avg_score, total_jobs, etc"
    )


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str = Field(description="Error message")
    detail: str = Field(default="", description="Additional details")
    error_code: str = Field(default="INTERNAL_ERROR")

