"""Pydantic request/response schemas for the AgentOps API."""

import uuid
from datetime import datetime
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.models import (
    AuditJobStatus,
    FindingCategory,
    FindingFixStatus,
    FindingSeverity,
)

GITHUB_URL_PREFIX = "https://github.com/"


def extract_repo_name(repo_url: str) -> str:
    """Validate repo_url is a GitHub URL and extract its 'owner/repo' name."""
    if not repo_url.startswith(GITHUB_URL_PREFIX):
        raise ValueError(f"repo_url must start with '{GITHUB_URL_PREFIX}'")

    path = urlparse(repo_url).path.strip("/")
    if path.endswith(".git"):
        path = path[: -len(".git")]

    parts = [segment for segment in path.split("/") if segment]
    if len(parts) < 2:
        raise ValueError("repo_url must include both an owner and a repository name")

    return "/".join(parts[:2])


class AuditJobCreate(BaseModel):
    """Request body for creating a new audit job."""

    repo_url: str = Field(
        ..., description=f"GitHub repository URL, must start with '{GITHUB_URL_PREFIX}'"
    )

    @field_validator("repo_url")
    @classmethod
    def validate_github_url(cls, value: str) -> str:
        """Ensure repo_url is a well-formed GitHub repository URL."""
        extract_repo_name(value)
        return value


class AuditJobCreateResponse(BaseModel):
    """Response returned immediately after an audit job is created and queued."""

    audit_id: uuid.UUID
    status: AuditJobStatus
    repo_url: str
    repo_name: str | None = None


class AuditJobResponse(BaseModel):
    """Full representation of an audit job."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    repo_url: str
    repo_name: str | None
    status: AuditJobStatus
    health_score: int | None
    created_at: datetime
    completed_at: datetime | None


class FindingResponse(BaseModel):
    """Full representation of a finding."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    audit_id: uuid.UUID
    agent_role: str
    category: FindingCategory
    severity: FindingSeverity
    title: str
    detail: str
    file_path: str | None
    line_number: int | None
    confidence: float
    auto_fix_available: bool
    fix_status: FindingFixStatus
    pr_url: str | None
    created_at: datetime


class FindingSummaryResponse(BaseModel):
    """Finding counts grouped by severity and by category for an audit."""

    critical: int
    high: int
    medium: int
    low: int
    by_category: dict[str, int]


class EvaluationResponse(BaseModel):
    """Full representation of an evaluation metric."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    audit_id: uuid.UUID
    metric: str
    score: float
    feedback: str | None
    evaluated_at: datetime


class FixApproveResponse(BaseModel):
    """Response returned after approving a finding's auto-fix."""

    finding_id: uuid.UUID
    fix_status: FindingFixStatus
    message: str


class AuditSpanResponse(BaseModel):
    """Full representation of a single timed span within an audit's timeline."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    span_name: str
    status: str
    started_at: str
    ended_at: str | None
    duration_ms: float | None
    input_summary: str | None
    output_summary: str | None
    error: str | None
    metadata: dict | None


class AuditTimelineResponse(BaseModel):
    """Full observability timeline for a single audit."""

    audit_id: str
    repo_name: str | None
    status: AuditJobStatus
    total_duration_ms: float
    spans: list[AuditSpanResponse]
