"""Lightweight audit tracer for observability.

Records every pipeline step as a timed span in the database, so the
full sequence of what happened inside an audit (and how long each
step took) can be reconstructed later via the timeline API.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.audit_span import AuditSpan

logger = logging.getLogger(__name__)


class AuditTracer:
    """Tracer for a single audit run.

    Use as an async context manager for each pipeline step.

    Usage:
        tracer = AuditTracer(audit_id, db)

        async with tracer.span("repo_analyzer",
                               input_summary="tiangolo/fastapi") as span:
            result = await analyze_repository(repo_url)
            span.output_summary = f"{result['total_files']} files"
            span.metadata_ = {"languages": result["languages"]}

    Recording a span must never be the reason an audit fails: any
    failure while persisting span bookkeeping is logged and swallowed
    rather than propagated. Only exceptions raised by the caller's own
    code inside the `async with` block are re-raised.
    """

    def __init__(self, audit_id: UUID, db: AsyncSession):
        self.audit_id = audit_id
        self.db = db

    @asynccontextmanager
    async def span(
        self,
        span_name: str,
        input_summary: str | None = None,
        metadata: dict | None = None,
    ):
        """Create a span, yield it for the caller to annotate, then finalize it.

        Timing is always recorded via try/finally. If persisting the
        span to the database fails at any point, the failure is
        logged and swallowed so it can never take down the audit that
        is being traced.
        """
        audit_span = AuditSpan(
            audit_id=self.audit_id,
            span_name=span_name,
            status="running",
            started_at=datetime.utcnow(),
            input_summary=input_summary,
            metadata_=metadata or {},
        )

        try:
            self.db.add(audit_span)
            await self.db.commit()
            await self.db.refresh(audit_span)
        except Exception:
            logger.warning(
                "Failed to create audit span %r — continuing without persistence",
                span_name,
                exc_info=True,
            )
            try:
                await self.db.rollback()
            except Exception:
                logger.warning(
                    "Failed to roll back session after span creation error for %r",
                    span_name,
                    exc_info=True,
                )

        try:
            yield audit_span
            if audit_span.status == "running":
                audit_span.status = "success"
        except Exception as e:
            audit_span.status = "failed"
            audit_span.error = str(e)
            raise
        finally:
            audit_span.ended_at = datetime.utcnow()
            audit_span.duration_ms = (
                audit_span.ended_at - audit_span.started_at
            ).total_seconds() * 1000
            try:
                await self.db.commit()
            except Exception:
                logger.warning(
                    "Failed to persist final state for span %r — continuing",
                    span_name,
                    exc_info=True,
                )
                try:
                    await self.db.rollback()
                except Exception:
                    logger.warning(
                        "Failed to roll back session after span finalization "
                        "error for %r",
                        span_name,
                        exc_info=True,
                    )
            logger.info(
                "Span [%s] %s in %.0fms",
                span_name,
                audit_span.status,
                audit_span.duration_ms,
            )


async def get_audit_timeline(audit_id: UUID, db: AsyncSession) -> list[dict]:
    """Return the full timeline for an audit as a list of span dicts.

    Ordered by started_at ascending.
    """
    result = await db.execute(
        select(AuditSpan)
        .where(AuditSpan.audit_id == audit_id)
        .order_by(AuditSpan.started_at)
    )
    spans = result.scalars().all()

    return [
        {
            "id": str(span.id),
            "span_name": span.span_name,
            "status": span.status,
            "started_at": span.started_at.isoformat(),
            "ended_at": (span.ended_at.isoformat() if span.ended_at else None),
            "duration_ms": span.duration_ms,
            "input_summary": span.input_summary,
            "output_summary": span.output_summary,
            "error": span.error,
            "metadata": span.metadata_,
        }
        for span in spans
    ]
