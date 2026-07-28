"""Manager agent that synthesises findings from all specialist agents.

Deduplicates findings, sorts them by severity and confidence, and
computes an overall repository health score. Pure Python — no LLM call.
"""

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

SEVERITY_PENALTY = {"critical": 12, "high": 6, "medium": 3, "low": 1}
SEVERITY_PENALTY_CAP = {"critical": 36, "high": 18, "medium": 15, "low": 7}


async def synthesise_findings(all_findings: list[dict], repo_map: dict) -> dict:
    """Deduplicate, sort, and score findings from all specialist agents."""
    deduped: dict[str, dict] = {}
    for finding in all_findings:
        title = finding.get("title")
        confidence = finding.get("confidence") or 0.0
        existing = deduped.get(title)
        if existing is None or confidence > (existing.get("confidence") or 0.0):
            deduped[title] = finding

    findings = list(deduped.values())
    findings.sort(
        key=lambda f: (
            SEVERITY_ORDER.get(f.get("severity"), len(SEVERITY_ORDER)),
            -(f.get("confidence") or 0.0),
        )
    )

    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for finding in findings:
        severity = finding.get("severity")
        if severity in counts:
            counts[severity] += 1

    health_score = 100
    for severity, count in counts.items():
        penalty = min(
            count * SEVERITY_PENALTY[severity], SEVERITY_PENALTY_CAP[severity]
        )
        health_score -= penalty
    health_score = max(health_score, 0)

    return {
        "health_score": health_score,
        "findings": findings,
        "summary": {
            "critical": counts["critical"],
            "high": counts["high"],
            "medium": counts["medium"],
            "low": counts["low"],
            "total": len(findings),
        },
    }
