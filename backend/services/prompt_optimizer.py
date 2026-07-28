"""Service responsible for the self-improvement loop.

After every audit, checks recent evaluation scores; if the average
agent success rate has fallen below the quality threshold, generates
an improved system prompt for the worst-performing agent role,
benchmarks it against the current one, and promotes it if it scores
higher.
"""

import logging
from pathlib import Path

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agents._llm_common import MODEL, client
from backend.models import (
    AgentRun,
    AgentRunStatus,
    AuditJob,
    Evaluation,
    Finding,
    PromptVariation,
)

logger = logging.getLogger(__name__)

SUCCESS_RATE_THRESHOLD = 0.80
PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "agents" / "prompts"


async def get_active_prompt(agent_role: str, db: AsyncSession) -> str:
    """Get the currently active prompt for an agent role.

    First checks the PromptVariations table for an is_active=True row.
    Falls back to reading the static prompt file under agents/prompts/.
    """
    result = await db.execute(
        select(PromptVariation)
        .where(
            PromptVariation.agent_role == agent_role,
            PromptVariation.is_active.is_(True),
        )
        .order_by(desc(PromptVariation.promoted_at))
        .limit(1)
    )
    active = result.scalar_one_or_none()
    if active is not None:
        return active.prompt_text

    prompt_path = PROMPTS_DIR / f"{agent_role}.txt"
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")

    return ""


async def generate_improved_prompt(
    agent_role: str, current_prompt: str, failure_reason: str
) -> str:
    """Use an LLM to generate an improved system prompt for an underperforming agent."""
    meta_prompt = f"""You are an expert at writing system prompts for AI agents.
The following agent is underperforming.

Agent role: {agent_role}
Current prompt: {current_prompt}
Failure reason: {failure_reason}

Write an improved system prompt that addresses the failure reason.
Keep the same general structure but make it more specific and
clear about expected output format.
Return only the improved prompt text, nothing else."""

    response = await client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": meta_prompt}],
        max_tokens=1000,
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()


async def _find_worst_agent_role(db: AsyncSession) -> tuple[str, str] | None:
    """Find the agent role with the most failed runs, and a human-readable failure reason."""
    result = await db.execute(
        select(AgentRun.agent_role, func.count())
        .where(AgentRun.status == AgentRunStatus.FAILED)
        .group_by(AgentRun.agent_role)
        .order_by(desc(func.count()))
        .limit(1)
    )
    row = result.first()
    if row is None:
        return None
    agent_role, failure_count = row
    return (
        agent_role,
        f"{failure_count} recent agent runs failed for role '{agent_role}'",
    )


async def _benchmark_prompt_score(agent_role: str, db: AsyncSession) -> float:
    """Simplified benchmark: avg confidence of findings from the last 3 audits using this agent."""
    result = await db.execute(
        select(Finding.confidence)
        .where(Finding.agent_role == agent_role)
        .order_by(desc(Finding.created_at))
        .limit(3)
    )
    scores = [row[0] for row in result.all()]
    if not scores:
        return 0.0
    return sum(scores) / len(scores)


async def check_and_improve_prompts(db: AsyncSession) -> None:
    """Analyze recent evaluation scores and improve agent prompts if quality is below threshold.

    Never raises — the self-improvement loop is best-effort and must
    not take down the audit pipeline that triggers it.
    """
    try:
        result = await db.execute(
            select(AuditJob).order_by(desc(AuditJob.created_at)).limit(5)
        )
        recent_audits = result.scalars().all()
        if not recent_audits:
            logger.info("No audits found — skipping prompt optimizer")
            return

        audit_ids = [a.id for a in recent_audits]

        eval_result = await db.execute(
            select(Evaluation.score).where(
                Evaluation.audit_id.in_(audit_ids),
                Evaluation.metric == "agent_success_rate",
            )
        )
        scores = [row[0] for row in eval_result.all()]
        if not scores:
            logger.info(
                "No agent_success_rate evaluations found — skipping prompt optimizer"
            )
            return

        avg_success_rate = sum(scores) / len(scores)

        if avg_success_rate >= SUCCESS_RATE_THRESHOLD:
            logger.info(
                "All agents performing well (avg success rate %.3f)", avg_success_rate
            )
            return

        worst = await _find_worst_agent_role(db)
        if worst is None:
            logger.info("Success rate is low but no failed agent runs found — skipping")
            return
        agent_role, failure_reason = worst

        current_prompt = await get_active_prompt(agent_role, db)
        old_score = await _benchmark_prompt_score(agent_role, db)

        new_prompt_text = await generate_improved_prompt(
            agent_role, current_prompt, failure_reason
        )

        new_variation = PromptVariation(
            agent_role=agent_role,
            prompt_text=new_prompt_text,
            is_active=False,
        )
        db.add(new_variation)

        # Simplified benchmark: the new prompt has not produced any findings
        # yet, so it is scored with the same formula against its own (empty)
        # history. A real score only becomes available once it has been
        # promoted and used in production audits.
        new_score = await _benchmark_prompt_score(agent_role, db)

        if new_score > old_score:
            result = await db.execute(
                select(PromptVariation).where(
                    PromptVariation.agent_role == agent_role,
                    PromptVariation.is_active.is_(True),
                )
            )
            for active in result.scalars().all():
                active.is_active = False

            new_variation.is_active = True
            new_variation.avg_score = new_score
            logger.info(
                "Promoted new prompt for agent role %s (score %.3f)",
                agent_role,
                new_score,
            )
        else:
            new_variation.avg_score = new_score
            logger.info(
                "New prompt for agent role %s did not improve score (%.3f <= %.3f); not promoted",
                agent_role,
                new_score,
                old_score,
            )

        await db.commit()
    except Exception:
        logger.exception("Prompt optimizer failed")
