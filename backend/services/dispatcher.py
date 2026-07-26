"""Service responsible for dispatching audit jobs to the agent team.

Coordinates spawning the manager agent, tracking agent run lifecycle,
and persisting results back to the database.
"""

import logging
import uuid
from datetime import datetime

from backend.db import SessionLocal
from backend.models import AuditJob, AuditJobStatus

logger = logging.getLogger(__name__)


async def dispatch_audit(audit_id: uuid.UUID) -> None:
    """Run the audit pipeline for the given audit job to completion.

    TODO: Wire AutoGen agent team here in V1 Week 2
    """
    logger.info("Dispatching audit job %s", audit_id)

    async with SessionLocal() as session:
        audit_job = await session.get(AuditJob, audit_id)
        if audit_job is None:
            logger.error("Audit job %s not found; cannot dispatch", audit_id)
            return

        audit_job.status = AuditJobStatus.ANALYZING
        await session.commit()

        # TODO: Wire AutoGen agent team here in V1 Week 2
        audit_job.status = AuditJobStatus.COMPLETE
        audit_job.health_score = 0
        audit_job.completed_at = datetime.utcnow()
        await session.commit()

        logger.info("Audit job %s complete", audit_id)
