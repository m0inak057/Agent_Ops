"""ORM model representing a single timed step within an audit pipeline.

Records every step in an audit pipeline as a timed span, enabling full
observability of what happened inside each audit.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db import Base

if TYPE_CHECKING:
    from backend.models.audit_job import AuditJob


class AuditSpan(Base):
    """Represents a single timed step (span) within an audit pipeline run."""

    __tablename__ = "audit_spans"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    audit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("audit_jobs.id"), nullable=False
    )
    span_name: Mapped[str] = mapped_column(String, nullable=False)
    # Examples: "repo_analyzer", "github_mcp.get_repository_tree",
    # "unified_agent", "confidence_pipeline", "manager",
    # "notifier", "evaluation", "prompt_optimizer"

    status: Mapped[str] = mapped_column(String, nullable=False, default="running")
    # running / success / failed / skipped

    started_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)

    input_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Brief description of what went in, e.g. "repo: tiangolo/fastapi"

    output_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Brief description of the result, e.g. "137 files, 42 deps detected"

    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Error message if status=failed

    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    # Optional extra data, e.g. {"files_fetched": 5, "findings": 8}

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    audit_job: Mapped["AuditJob"] = relationship(
        "AuditJob", back_populates="audit_spans"
    )

    def __repr__(self) -> str:
        return (
            f"<AuditSpan {self.span_name} "
            f"status={self.status} "
            f"duration={self.duration_ms}ms>"
        )
