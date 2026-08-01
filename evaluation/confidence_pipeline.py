"""Pipeline for validating agent findings before they reach the user.

Runs every finding through rule-based evidence checks and applies
confidence thresholds to decide whether a finding is surfaced,
requires approval before auto-fix, or is discarded outright.
"""

import logging

logger = logging.getLogger(__name__)


async def validate_single_finding(finding: dict, repo_map: dict) -> dict | None:
    """Validates a single finding using rule-based checks only.

    No LLM call — saves 6-10 API calls per audit.

    Returns None if the finding should be discarded.
    """
    try:
        finding = dict(finding)
        confidence = finding.get("confidence") or 0.5

        # Rule 1: Must have non-empty title
        if not (finding.get("title") or "").strip():
            return None

        # Rule 2: Detail must be substantial
        detail = finding.get("detail") or ""
        if len(detail) < 20:
            return None
        if len(detail) < 50:
            confidence -= 0.1

        # Rule 3: If file_path given, check it exists in tree
        file_path = finding.get("file_path")
        if file_path and file_path not in repo_map.get("file_tree", []):
            confidence -= 0.15

        # Rule 4: Discard if confidence too low
        confidence = max(0.0, min(1.0, confidence))
        if confidence < 0.40:
            return None

        # Rule 5: Apply auto_fix threshold
        if confidence < 0.95:
            finding["auto_fix_available"] = False

        finding["confidence"] = confidence
        finding["validation_reasoning"] = "rule-based validation"
        return finding
    except Exception as e:
        logger.warning("Validation failed for finding %r: %s", finding.get("title"), e)
        return None


async def validate_findings(findings: list[dict], repo_map: dict) -> list[dict]:
    """Validates all findings using rule-based checks."""
    validated = []
    for finding in findings:
        result = await validate_single_finding(finding, repo_map)
        if result is not None:
            validated.append(result)
    return validated
