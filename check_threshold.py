"""Quality gate script for CI/CD pipeline.

Reads the latest evaluation scores from the database and fails the
build if the averages across recent audits fall below the configured
thresholds.
"""

import asyncio
import os
import sys

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.models import AuditJob, Evaluation

QUALITY_GATE_RULES = {
    "agent_success_rate": {"operator": ">=", "threshold": 0.80},
    "average_confidence": {"operator": ">=", "threshold": 0.70},
    "audit_quality_finding_relevance": {"operator": ">=", "threshold": 0.70},
}


async def check_thresholds():
    """Check the average of recent evaluation scores against QUALITY_GATE_RULES."""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("No DATABASE_URL — skipping quality gate in CI")
        sys.exit(0)

    engine = create_async_engine(database_url)
    async_session = async_sessionmaker(engine, class_=AsyncSession)

    async with async_session() as db:
        # Get last 5 completed audits
        result = await db.execute(
            select(AuditJob)
            .where(AuditJob.status == "complete")
            .order_by(desc(AuditJob.created_at))
            .limit(5)
        )
        recent_audits = result.scalars().all()

        if not recent_audits:
            print("No completed audits found — skipping quality gate")
            sys.exit(0)

        audit_ids = [a.id for a in recent_audits]

        # Get evaluations for these audits
        eval_result = await db.execute(
            select(Evaluation).where(Evaluation.audit_id.in_(audit_ids))
        )
        evaluations = eval_result.scalars().all()

        # Group by metric and average
        metric_scores: dict[str, list[float]] = {}
        for ev in evaluations:
            metric_scores.setdefault(ev.metric, []).append(ev.score)

        avg_scores = {
            metric: sum(scores) / len(scores)
            for metric, scores in metric_scores.items()
        }

        # Check thresholds
        failed = []
        passed = []

        for metric, rule in QUALITY_GATE_RULES.items():
            if metric not in avg_scores:
                print(f"SKIP  {metric}: no data")
                continue

            score = avg_scores[metric]
            threshold = rule["threshold"]

            if score >= threshold:
                passed.append(f"PASS  {metric}: {score:.3f} (required >= {threshold})")
            else:
                failed.append(f"FAIL  {metric}: {score:.3f} (required >= {threshold})")

        print("\nQuality Gate Results")
        print("=" * 50)
        for p in passed:
            print(p)
        for f in failed:
            print(f)

        if failed:
            print("\nQuality gate FAILED — deployment blocked")
            sys.exit(1)
        else:
            print("\nQuality gate PASSED")
            sys.exit(0)


if __name__ == "__main__":
    asyncio.run(check_thresholds())
