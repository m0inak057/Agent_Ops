"""ORM model representing a single agent's execution within an audit job.

Tracks which agent ran, its status, timing, and the tool executions
and findings it produced.
"""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db import Base

if TYPE_CHECKING:
    from backend.models.audit_job import AuditJob
    from backend.models.tool_execution import ToolExecution


class AgentRunStatus(str, enum.Enum):
    """The lifecycle status of an agent run."""

    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRIED = "retried"


class AgentRun(Base):
    """Represents a single agent's execution within an audit job."""

    __tablename__ = "agent_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    audit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("audit_jobs.id"), nullable=False
    )
    agent_role: Mapped[str] = mapped_column(String, nullable=False)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    turns: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    findings_produced: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[AgentRunStatus] = mapped_column(
        Enum(AgentRunStatus, name="agent_run_status"),
        default=AgentRunStatus.RUNNING,
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    audit_job: Mapped["AuditJob"] = relationship(
        "AuditJob", back_populates="agent_runs"
    )
    tool_executions: Mapped[list["ToolExecution"]] = relationship(
        "ToolExecution", back_populates="agent_run", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<AgentRun id={self.id} agent_role={self.agent_role!r} status={self.status}>"
