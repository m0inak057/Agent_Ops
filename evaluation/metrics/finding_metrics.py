"""Metrics for scoring the findings produced by a single audit.

Computes deterministic statistics directly from the Finding table:
average confidence, severity distribution, and auto-fix availability
rate.
"""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Finding

logger = logging.getLogger(__name__)


async def compute_finding_metrics(audit_id: str, db: AsyncSession) -> list[dict]:
    """Compute finding-level metrics for a single audit."""
    try:
        result = await db.execute(
            select(Finding).where(Finding.audit_id == uuid.UUID(str(audit_id)))
        )
        findings = result.scalars().all()

        if not findings:
            return []

        total = len(findings)
        avg_confidence = sum(f.confidence for f in findings) / total

        metrics = [
            {
                "metric": "average_confidence",
                "score": avg_confidence,
                "feedback": f"Average confidence {avg_confidence:.3f} across {total} findings",
            }
        ]

        severity_counts: dict[str, int] = {}
        for f in findings:
            severity = f.severity.value if hasattr(f.severity, "value") else f.severity
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        for severity, count in severity_counts.items():
            pct = count / total
            metrics.append(
                {
                    "metric": f"finding_distribution_{severity}",
                    "score": pct,
                    "feedback": f"{count}/{total} findings are {severity} severity ({pct:.1%})",
                }
            )

        auto_fix_count = sum(1 for f in findings if f.auto_fix_available)
        auto_fix_rate = auto_fix_count / total
        metrics.append(
            {
                "metric": "auto_fix_rate",
                "score": auto_fix_rate,
                "feedback": (
                    f"{auto_fix_count}/{total} findings are auto-fixable ({auto_fix_rate:.1%})"
                ),
            }
        )

        return metrics
    except Exception as e:
        logger.warning(
            "Finding metric computation failed for audit %s: %s", audit_id, e
        )
        return []
