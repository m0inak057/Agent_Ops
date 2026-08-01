"""Service responsible for dispatching audit jobs to the agent team.

Runs the repo analyzer, then a single unified agent call over the repo
map, synthesises the findings, and persists everything back to the
database.
"""

import logging
import uuid
from datetime import datetime

from sqlalchemy import select

from backend.db import SessionLocal
from backend.models import AgentRun, AgentRunStatus, AuditJob, AuditJobStatus, Finding

from agents.manager import synthesise_findings
from agents.repo_analyzer import analyze_repository
from agents.unified_agent import run_unified_audit
from backend.services.notifier import notify_new_findings
from backend.services.prompt_optimizer import check_and_improve_prompts
from evaluation.confidence_pipeline import validate_findings
from evaluation.framework import run_evaluation

logger = logging.getLogger(__name__)


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
                audit_id=audit_id,
                agent_role="repo_analyzer",
                status=AgentRunStatus.RUNNING,
            )
            session.add(repo_analyzer_run)
            await session.commit()

            repo_map = await analyze_repository(audit_job.repo_url)

            repo_analyzer_run.status = AgentRunStatus.SUCCESS
            repo_analyzer_run.ended_at = datetime.utcnow()
            await session.commit()

            # Single unified agent call — replaces 7 separate LLM calls
            logger.info(f"Running unified agent for audit {audit_id}")
            unified_run = AgentRun(
                audit_id=audit_id,
                agent_role="unified",
                status=AgentRunStatus.RUNNING,
            )
            session.add(unified_run)
            await session.commit()

            try:
                all_findings = await run_unified_audit(repo_map)
                unified_run.status = AgentRunStatus.SUCCESS
                unified_run.findings_produced = len(all_findings)
            except Exception as e:
                logger.error(f"Unified agent failed: {e}")
                all_findings = []
                unified_run.status = AgentRunStatus.FAILED

            unified_run.ended_at = datetime.utcnow()
            await session.commit()

            validated_findings = await validate_findings(all_findings, repo_map)

            result = await synthesise_findings(validated_findings, repo_map)

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

            try:
                findings_result = await session.execute(
                    select(Finding).where(Finding.audit_id == audit_id)
                )
                written_findings = findings_result.scalars().all()
                await notify_new_findings(audit_job, written_findings, session)
            except Exception as e:
                logger.warning("Notifier failed: %s", e)

            try:
                await run_evaluation(str(audit_id), repo_map, session)
            except Exception as e:
                logger.error("Evaluation failed for %s: %s", audit_id, e)
                # Never fail the audit because evaluation failed

            try:
                await check_and_improve_prompts(session)
            except Exception as e:
                logger.error("Prompt optimizer failed: %s", e)
                # Never fail the audit because the optimizer failed

        except Exception:
            logger.exception("Audit job %s failed", audit_id)
            await session.rollback()
            audit_job = await session.get(AuditJob, audit_id)
            if audit_job is not None:
                audit_job.status = AuditJobStatus.FAILED
                await session.commit()
