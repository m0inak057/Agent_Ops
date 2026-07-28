"""Top-level evaluation orchestration.

Runs the full metric suite (agent, finding, system, and LLM-judge
metrics) for a completed audit job and persists the results to the
Evaluations table.
"""

import asyncio
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import AuditJob, Evaluation, Finding
from evaluation.metrics.agent_metrics import compute_agent_metrics
from evaluation.metrics.finding_metrics import compute_finding_metrics
from evaluation.metrics.llm_judge import judge_audit_quality
from evaluation.metrics.system_metrics import compute_system_metrics

logger = logging.getLogger(__name__)


async def run_evaluation(audit_id: str, repo_map: dict, db: AsyncSession) -> None:
    """Run the full evaluation suite for a completed audit and persist the scores.

    Never raises — evaluation is best-effort and must not take down
    the audit pipeline that calls it.
    """
    try:
        audit_uuid = uuid.UUID(str(audit_id))

        audit_job = await db.get(AuditJob, audit_uuid)
        if audit_job is None:
            logger.error("Audit job %s not found; skipping evaluation", audit_id)
            return

        result = await db.execute(select(Finding).where(Finding.audit_id == audit_uuid))
        findings = result.scalars().all()
        findings_as_dicts = [
            {
                "title": f.title,
                "severity": (
                    f.severity.value if hasattr(f.severity, "value") else f.severity
                ),
                "category": (
                    f.category.value if hasattr(f.category, "value") else f.category
                ),
            }
            for f in findings
        ]

        agent_metrics, finding_metrics, system_metrics, judge_metrics = (
            await asyncio.gather(
                compute_agent_metrics(audit_id, db),
                compute_finding_metrics(audit_id, db),
                compute_system_metrics(audit_job, db),
                judge_audit_quality(audit_id, findings_as_dicts, repo_map),
                return_exceptions=True,
            )
        )

        all_metrics: list[dict] = []
        for metrics in (agent_metrics, finding_metrics, system_metrics, judge_metrics):
            if isinstance(metrics, Exception):
                logger.warning("Metric computation raised: %s", metrics)
                continue
            all_metrics.extend(metrics)

        for metric in all_metrics:
            db.add(
                Evaluation(
                    audit_id=audit_uuid,
                    metric=metric["metric"],
                    score=metric["score"],
                    feedback=metric.get("feedback"),
                )
            )
        await db.commit()

        logger.info(
            "Evaluation complete for audit %s: %d metrics recorded",
            audit_id,
            len(all_metrics),
        )
    except Exception:
        logger.exception("Evaluation failed for audit %s", audit_id)
