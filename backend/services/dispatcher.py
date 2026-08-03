"""Service responsible for dispatching audit jobs to the agent team.

Runs the repo analyzer, then a single unified agent call over the repo
map, synthesises the findings, and persists everything back to the
database. Every step is recorded as a timed span via AuditTracer for
observability.
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
from backend.services.tracer import AuditTracer
from evaluation.confidence_pipeline import validate_findings
from evaluation.framework import run_evaluation

logger = logging.getLogger(__name__)


def _count_by_category(findings: list[dict]) -> dict:
    """Count findings grouped by category."""
    counts: dict[str, int] = {}
    for f in findings:
        cat = f.get("category", "unknown")
        counts[cat] = counts.get(cat, 0) + 1
    return counts


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

            tracer = AuditTracer(audit_id, session)

            # Step 1 — repo_analyzer
            repo_analyzer_run = AgentRun(
                audit_id=audit_id,
                agent_role="repo_analyzer",
                status=AgentRunStatus.RUNNING,
            )
            session.add(repo_analyzer_run)
            await session.commit()

            async with tracer.span(
                "repo_analyzer", input_summary=f"repo: {audit_job.repo_name}"
            ) as span:
                repo_map = await analyze_repository(audit_job.repo_url)
                span.output_summary = (
                    f"{repo_map.get('total_files', 0)} files, "
                    f"{repo_map.get('project_type', 'unknown')} project"
                )
                span.metadata_ = {
                    "languages": repo_map.get("languages", []),
                    "has_dockerfile": repo_map.get("has_dockerfile", False),
                    "has_ci_cd": repo_map.get("has_ci_cd", False),
                    "has_tests": repo_map.get("has_tests", False),
                }

            repo_analyzer_run.status = AgentRunStatus.SUCCESS
            repo_analyzer_run.ended_at = datetime.utcnow()
            await session.commit()

            # Step 2 — unified_agent (single unified call, replaces 7 specialist calls)
            logger.info(f"Running unified agent for audit {audit_id}")
            unified_run = AgentRun(
                audit_id=audit_id,
                agent_role="unified",
                status=AgentRunStatus.RUNNING,
            )
            session.add(unified_run)
            await session.commit()

            async with tracer.span(
                "unified_agent",
                input_summary=f"auditing {repo_map.get('project_type', 'repo')}",
            ) as span:
                try:
                    all_findings = await run_unified_audit(repo_map)
                    unified_run.status = AgentRunStatus.SUCCESS
                    unified_run.findings_produced = len(all_findings)
                except Exception as e:
                    logger.error(f"Unified agent failed: {e}")
                    all_findings = []
                    unified_run.status = AgentRunStatus.FAILED
                    span.status = "failed"
                    span.error = str(e)
                span.output_summary = f"{len(all_findings)} raw findings"
                span.metadata_ = {
                    "findings_by_category": _count_by_category(all_findings)
                }

            unified_run.ended_at = datetime.utcnow()
            await session.commit()

            # Step 3 — confidence_pipeline
            async with tracer.span(
                "confidence_pipeline",
                input_summary=f"{len(all_findings)} findings to validate",
            ) as span:
                validated_findings = await validate_findings(all_findings, repo_map)
                span.output_summary = (
                    f"{len(validated_findings)} accepted, "
                    f"{len(all_findings) - len(validated_findings)} rejected"
                )

            # Step 4 — manager
            async with tracer.span(
                "manager",
                input_summary=f"{len(validated_findings)} validated findings",
            ) as span:
                result = await synthesise_findings(validated_findings, repo_map)
                span.output_summary = (
                    f"health_score: {result['health_score']}, "
                    f"total: {result['summary']['total']}"
                )
                span.metadata_ = result["summary"]

            # Step 5 — db_write
            async with tracer.span(
                "db_write",
                input_summary=f"writing {len(result['findings'])} findings",
            ) as span:
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
                span.output_summary = f"{len(result['findings'])} findings persisted"

            logger.info("Audit job %s complete", audit_id)

            # Step 6 — notifier (best-effort — must never fail the audit)
            try:
                async with tracer.span("notifier") as span:
                    findings_result = await session.execute(
                        select(Finding).where(Finding.audit_id == audit_id)
                    )
                    written_findings = findings_result.scalars().all()
                    await notify_new_findings(audit_job, written_findings, session)
                    span.output_summary = "diff complete"
            except Exception as e:
                logger.warning("Notifier failed: %s", e)

            # Step 7 — evaluation (best-effort — must never fail the audit)
            try:
                async with tracer.span("evaluation") as span:
                    await run_evaluation(str(audit_id), repo_map, session)
                    span.output_summary = "evaluation complete"
            except Exception as e:
                logger.error("Evaluation failed for %s: %s", audit_id, e)
                # Never fail the audit because evaluation failed

            # Step 8 — prompt_optimizer (best-effort — must never fail the audit)
            try:
                async with tracer.span("prompt_optimizer") as span:
                    await check_and_improve_prompts(session)
                    span.output_summary = "optimization check complete"
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
