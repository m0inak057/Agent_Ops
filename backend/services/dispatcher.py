"""Service responsible for dispatching audit jobs to the agent team.

Runs the repo analyzer, fans the repo map out to the four specialist
agents concurrently, synthesises their findings, and persists everything
back to the database.
"""

import asyncio
import logging
import uuid
from datetime import datetime

from backend.db import SessionLocal
from backend.models import AgentRun, AgentRunStatus, AuditJob, AuditJobStatus, Finding

from agents.code_quality import run_code_quality_audit
from agents.devops import run_devops_audit
from agents.manager import synthesise_findings
from agents.repo_analyzer import analyze_repository
from agents.security import run_security_audit
from agents.testing import run_testing_audit

logger = logging.getLogger(__name__)

SPECIALIST_AGENTS = [
    ("security", run_security_audit),
    ("code_quality", run_code_quality_audit),
    ("testing", run_testing_audit),
    ("devops", run_devops_audit),
]


async def dispatch_audit(audit_id: uuid.UUID) -> None:
    """Run the full agent pipeline for the given audit job to completion."""
    logger.info("Dispatching audit job %s", audit_id)

    async with SessionLocal() as session:
        try:
            audit_job = await session.get(AuditJob, audit_id)
            if audit_job is None:
                logger.error("Audit job %s not found; cannot dispatch", audit_id)
                return

            audit_job.status = AuditJobStatus.ANALYZING
            await session.commit()

            repo_analyzer_run = AgentRun(
                audit_id=audit_id, agent_role="repo_analyzer", status=AgentRunStatus.RUNNING
            )
            session.add(repo_analyzer_run)
            await session.commit()

            repo_map = await analyze_repository(audit_job.repo_url)

            repo_analyzer_run.status = AgentRunStatus.SUCCESS
            repo_analyzer_run.ended_at = datetime.utcnow()
            await session.commit()

            results = await asyncio.gather(
                *(agent_fn(repo_map) for _, agent_fn in SPECIALIST_AGENTS)
            )

            all_findings: list[dict] = []
            for (agent_role, _), findings in zip(SPECIALIST_AGENTS, results):
                session.add(
                    AgentRun(
                        audit_id=audit_id,
                        agent_role=agent_role,
                        status=AgentRunStatus.SUCCESS,
                        findings_produced=len(findings),
                        ended_at=datetime.utcnow(),
                    )
                )
                all_findings.extend(findings)
            await session.commit()

            result = await synthesise_findings(all_findings, repo_map)

            for finding in result["findings"]:
                session.add(
                    Finding(
                        audit_id=audit_id,
                        agent_role=finding.get("agent_role"),
                        category=finding.get("category"),
                        severity=finding.get("severity"),
                        title=finding.get("title"),
                        detail=finding.get("detail"),
                        file_path=finding.get("file_path"),
                        line_number=finding.get("line_number"),
                        confidence=finding.get("confidence"),
                        auto_fix_available=finding.get("auto_fix_available", False),
                    )
                )

            audit_job.status = AuditJobStatus.COMPLETE
            audit_job.health_score = result["health_score"]
            audit_job.completed_at = datetime.utcnow()
            await session.commit()

            logger.info("Audit job %s complete", audit_id)

        except Exception:
            logger.exception("Audit job %s failed", audit_id)
            await session.rollback()
            audit_job = await session.get(AuditJob, audit_id)
            if audit_job is not None:
                audit_job.status = AuditJobStatus.FAILED
                await session.commit()
