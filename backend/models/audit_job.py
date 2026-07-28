"""ORM model representing a single codebase audit job.

An audit job tracks a request to audit a repository, its status,
target repository metadata, and the agent runs it spawns.
"""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db import Base

if TYPE_CHECKING:
    from backend.models.agent_run import AgentRun
    from backend.models.evaluation import Evaluation
    from backend.models.finding import Finding


class AuditJobStatus(str, enum.Enum):
    """Lifecycle status of an audit job."""

    PENDING = "pending"
    ANALYZING = "analyzing"
    COMPLETE = "complete"
    FAILED = "failed"


class AuditJob(Base):
    """Represents a single audit job requested against a repository."""

    __tablename__ = "audit_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    repo_url: Mapped[str] = mapped_column(String, nullable=False)
    repo_name: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[AuditJobStatus] = mapped_column(
        Enum(AuditJobStatus, name="audit_job_status"),
        default=AuditJobStatus.PENDING,
        nullable=False,
    )
    health_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    agent_runs: Mapped[list["AgentRun"]] = relationship(
        "AgentRun", back_populates="audit_job", cascade="all, delete-orphan"
    )
    findings: Mapped[list["Finding"]] = relationship(
        "Finding", back_populates="audit_job", cascade="all, delete-orphan"
    )
    evaluations: Mapped[list["Evaluation"]] = relationship(
        "Evaluation", back_populates="audit_job", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<AuditJob id={self.id} repo_name={self.repo_name!r} status={self.status}>"
        )
