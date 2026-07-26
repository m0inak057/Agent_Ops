"""ORM model representing a candidate prompt variation for an agent.

Used by the prompt optimizer to track experimental prompt versions
and their associated evaluation performance.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.db import Base


class PromptVariation(Base):
    """Represents a candidate prompt variation for an agent under optimization."""

    __tablename__ = "prompt_variations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    agent_role: Mapped[str] = mapped_column(String, nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    avg_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    promoted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<PromptVariation id={self.id} agent_role={self.agent_role!r} "
            f"is_active={self.is_active}>"
        )
