"""ORM model representing a single MCP tool invocation by an agent.

Records the tool name, input arguments, output, timing, and outcome
of a tool call made during an agent run.
"""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db import Base

if TYPE_CHECKING:
    from backend.models.agent_run import AgentRun


class ToolExecutionStatus(str, enum.Enum):
    """The outcome status of a tool execution."""

    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


class ToolExecution(Base):
    """Represents a single MCP tool invocation made during an agent run."""

    __tablename__ = "tool_executions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_runs.id"), nullable=False
    )
    mcp_server: Mapped[str] = mapped_column(String, nullable=False)
    tool_name: Mapped[str] = mapped_column(String, nullable=False)
    input_args: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    output: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[ToolExecutionStatus] = mapped_column(
        Enum(ToolExecutionStatus, name="tool_execution_status"),
        default=ToolExecutionStatus.SUCCESS,
        nullable=False,
    )
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    called_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    agent_run: Mapped["AgentRun"] = relationship(
        "AgentRun", back_populates="tool_executions"
    )

    def __repr__(self) -> str:
        return (
            f"<ToolExecution id={self.id} mcp_server={self.mcp_server!r} "
            f"tool_name={self.tool_name!r} status={self.status}>"
        )
