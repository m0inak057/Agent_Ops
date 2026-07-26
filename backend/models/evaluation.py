"""ORM model representing an evaluation run against the benchmark dataset.

Tracks the evaluation's target (audit job or model configuration),
computed metrics, and status.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db import Base


class Evaluation(Base):
    """Represents a single scored metric for an audit job's evaluation."""

    __tablename__ = "evaluations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    audit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("audit_jobs.id"), nullable=False
    )
    metric: Mapped[str] = mapped_column(String, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    audit_job: Mapped["AuditJob"] = relationship("AuditJob", back_populates="evaluations")

    def __repr__(self) -> str:
        return f"<Evaluation id={self.id} metric={self.metric!r} score={self.score}>"
