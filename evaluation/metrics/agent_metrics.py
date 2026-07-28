"""Metrics for scoring individual agent performance.

Computes deterministic per-audit agent statistics directly from the
AgentRun table: success rate, turn count, finding production rate,
and resource usage (cost, tokens).
"""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import AgentRun, AgentRunStatus

logger = logging.getLogger(__name__)


async def compute_agent_metrics(audit_id: str, db: AsyncSession) -> list[dict]:
    """Compute deterministic agent-level metrics from DB logs for a single audit."""
    try:
        result = await db.execute(
            select(AgentRun).where(AgentRun.audit_id == uuid.UUID(str(audit_id)))
        )
        runs = result.scalars().all()

        if not runs:
            return []

        total = len(runs)
        successes = sum(1 for r in runs if r.status == AgentRunStatus.SUCCESS)
        success_rate = successes / total

        avg_turns = sum(r.turns for r in runs) / total

        total_findings = sum(r.findings_produced for r in runs)
        finding_production_rate = total_findings / total

        total_cost = sum(r.cost_usd for r in runs)
        total_tokens = sum(r.tokens_used for r in runs)

        return [
            {
                "metric": "agent_success_rate",
                "score": success_rate,
                "feedback": f"{successes}/{total} agent runs succeeded",
            },
            {
                "metric": "average_turn_count",
                "score": avg_turns,
                "feedback": f"Average {avg_turns:.2f} turns across {total} agent runs",
            },
            {
                "metric": "finding_production_rate",
                "score": finding_production_rate,
                "feedback": f"{total_findings} findings produced across {total} agent runs",
            },
            {
                "metric": "total_cost_usd",
                "score": total_cost,
                "feedback": f"${total_cost:.4f} total cost across {total} agent runs",
            },
            {
                "metric": "total_tokens",
                "score": float(total_tokens),
                "feedback": f"{total_tokens} total tokens used across {total} agent runs",
            },
        ]
    except Exception as e:
        logger.warning("Agent metric computation failed for audit %s: %s", audit_id, e)
        return []
