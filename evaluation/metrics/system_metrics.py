"""Metrics for scoring overall system performance of a single audit.

Computes deterministic latency, health score, and finding count
metrics directly from the AuditJob record and its findings.
"""

import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Finding

logger = logging.getLogger(__name__)


async def compute_system_metrics(audit_job, db: AsyncSession) -> list[dict]:
    """Compute system-level metrics for a single completed audit job."""
    try:
        metrics = []

        if audit_job.completed_at and audit_job.created_at:
            latency = (audit_job.completed_at - audit_job.created_at).total_seconds()
            metrics.append(
                {
                    "metric": "total_latency_seconds",
                    "score": latency,
                    "feedback": f"Audit completed in {latency:.1f} seconds",
                }
            )

        if audit_job.health_score is not None:
            metrics.append(
                {
                    "metric": "health_score",
                    "score": float(audit_job.health_score),
                    "feedback": f"Repository health score: {audit_job.health_score}",
                }
            )

        result = await db.execute(
            select(func.count())
            .select_from(Finding)
            .where(Finding.audit_id == audit_job.id)
        )
        finding_count = result.scalar() or 0
        metrics.append(
            {
                "metric": "finding_count",
                "score": float(finding_count),
                "feedback": f"{finding_count} findings produced",
            }
        )

        return metrics
    except Exception as e:
        logger.warning(
            "System metric computation failed for audit %s: %s", audit_job, e
        )
        return []
