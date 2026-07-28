"""Notification service for AgentOps.

Sends alerts when new issues are detected after a webhook-triggered
audit. In V5 this logs to console; future versions may send to
Slack, email, or a dashboard WebSocket.
"""

import logging

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import AuditJob, AuditJobStatus, Finding

logger = logging.getLogger(__name__)


async def notify_new_findings(
    audit_job: AuditJob, findings: list, db: AsyncSession
) -> None:
    """Compare new audit findings against the previous audit and log new issues."""
    result = await db.execute(
        select(AuditJob)
        .where(
            and_(
                AuditJob.repo_url == audit_job.repo_url,
                AuditJob.status == AuditJobStatus.COMPLETE,
                AuditJob.id != audit_job.id,
            )
        )
        .order_by(desc(AuditJob.created_at))
        .limit(1)
    )
    previous_audit = result.scalar_one_or_none()

    if not previous_audit:
        logger.info("First audit for %s — no comparison available", audit_job.repo_name)
        return

    prev_result = await db.execute(
        select(Finding.title).where(Finding.audit_id == previous_audit.id)
    )
    previous_titles = {row[0] for row in prev_result.fetchall()}

    new_findings = [f for f in findings if f.title not in previous_titles]
    resolved_count = len(previous_titles) - (len(findings) - len(new_findings))

    if new_findings:
        logger.warning(
            "NEW ISSUES DETECTED in %s: %d new finding(s)",
            audit_job.repo_name,
            len(new_findings),
        )
        for finding in new_findings:
            logger.warning(
                "  [%s] %s (confidence: %.0f%%)",
                finding.severity.upper(),
                finding.title,
                finding.confidence * 100,
            )
    else:
        logger.info("No new issues in %s", audit_job.repo_name)

    if resolved_count > 0:
        logger.info("%d issue(s) resolved since last audit", resolved_count)
