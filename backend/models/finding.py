"""ORM model representing a single finding produced by an audit agent.

Captures the finding's category, severity, confidence score,
supporting evidence, and location within the audited repository.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db import Base


class FindingCategory(str, enum.Enum):
    """The audit dimension a finding belongs to."""

    SECURITY = "security"
    CODE_QUALITY = "code_quality"
    ARCHITECTURE = "architecture"
    PERFORMANCE = "performance"
    TESTING = "testing"
    DEVOPS = "devops"
    DOCUMENTATION = "documentation"


class FindingSeverity(str, enum.Enum):
    """The severity level of a finding."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class FindingFixStatus(str, enum.Enum):
    """The lifecycle status of an auto-fix for a finding."""

    NONE = "none"
    SUGGESTED = "suggested"
    APPROVED = "approved"
    PR_CREATED = "pr_created"
    MERGED = "merged"


class Finding(Base):
    """Represents a single finding produced by an audit agent."""

    __tablename__ = "findings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    audit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("audit_jobs.id"), nullable=False
    )
    agent_role: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[FindingCategory] = mapped_column(
        Enum(FindingCategory, name="finding_category"), nullable=False
    )
    severity: Mapped[FindingSeverity] = mapped_column(
        Enum(FindingSeverity, name="finding_severity"), nullable=False
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    detail: Mapped[str] = mapped_column(Text, nullable=False)
    file_path: Mapped[str | None] = mapped_column(String, nullable=True)
    line_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    auto_fix_available: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    fix_status: Mapped[FindingFixStatus] = mapped_column(
        Enum(FindingFixStatus, name="finding_fix_status"),
        default=FindingFixStatus.NONE,
        nullable=False,
    )
    pr_url: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    audit_job: Mapped["AuditJob"] = relationship("AuditJob", back_populates="findings")

    def __repr__(self) -> str:
        return (
            f"<Finding id={self.id} category={self.category} "
            f"severity={self.severity} title={self.title!r}>"
        )
