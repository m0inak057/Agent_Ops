"""Pipeline for validating agent findings before they reach the user.

Runs every finding through a rule-based evidence check followed by an
LLM-as-a-judge relevance check, then applies confidence thresholds to
decide whether a finding is surfaced, requires approval before
auto-fix, or is discarded outright.
"""

import asyncio
import json
import logging

from agents._llm_common import client, MODEL

logger = logging.getLogger(__name__)

JUDGE_SYSTEM_PROMPT = """You are a senior software engineer validating whether a reported \
code issue is genuine and relevant. Score from 0.0 to 1.0.
1.0 = definitely real, evidence is clear and specific
0.5 = possibly real but context-dependent
0.0 = false positive, not actually a problem
Respond with JSON only: {"score": float, "reasoning": str}"""

MAX_CONCURRENT_VALIDATIONS = 10


def _evidence_check(finding: dict, repo_map: dict) -> float:
    """Rule-based evidence check. Returns a starting confidence for the finding."""
    confidence = finding.get("confidence") or 0.0

    title = finding.get("title") or ""
    detail = finding.get("detail") or ""

    if not title.strip() or not detail.strip() or len(detail) < 20:
        return 0.0

    file_path = finding.get("file_path")
    if file_path:
        file_tree = repo_map.get("file_tree", [])
        if file_path not in file_tree:
            confidence -= 0.2

    if len(detail) < 50:
        confidence -= 0.1

    return max(confidence, 0.0)


async def _judge_finding(finding: dict, repo_map: dict) -> float | None:
    """Call the LLM judge and return its score, or None on failure."""
    user_prompt = f"""Repository type: {repo_map.get('project_type')}
Finding title: {finding.get('title')}
Finding detail: {finding.get('detail')}
File path: {finding.get('file_path') or 'not specified'}

Is this a genuine issue for this type of project?"""

    try:
        response = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=300,
            temperature=0.1,
        )
        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            content = content.strip("`")
            if content.lower().startswith("json"):
                content = content[4:]
            content = content.strip()
        parsed = json.loads(content)
        return float(parsed["score"]), parsed.get("reasoning")
    except Exception as e:
        logger.warning("LLM judge call failed: %s", e)
        return None


async def validate_single_finding(finding: dict, repo_map: dict) -> dict | None:
    """Validate a single finding through all 3 steps.

    Returns None if the finding should be discarded.
    """
    try:
        finding = dict(finding)

        confidence = _evidence_check(finding, repo_map)

        reasoning = None
        if confidence > 0.5:
            judge_result = await _judge_finding(finding, repo_map)
            if judge_result is not None:
                llm_score, reasoning = judge_result
                confidence = confidence * llm_score

        finding["validation_reasoning"] = reasoning

        if confidence < 0.40:
            return None

        if confidence >= 0.95:
            pass
        elif confidence >= 0.85:
            finding["auto_fix_available"] = False
        else:
            finding["auto_fix_available"] = False

        finding["confidence"] = confidence
        return finding
    except Exception as e:
        logger.warning("Validation failed for finding %r: %s", finding.get("title"), e)
        return None


async def validate_findings(findings: list[dict], repo_map: dict) -> list[dict]:
    """Validate every finding and return only those that passed."""
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_VALIDATIONS)

    async def _bounded(finding: dict):
        async with semaphore:
            return await validate_single_finding(finding, repo_map)

    try:
        results = await asyncio.gather(
            *(_bounded(finding) for finding in findings), return_exceptions=True
        )
    except Exception as e:
        logger.warning("Confidence pipeline failed entirely: %s", e)
        return []

    validated = []
    for result in results:
        if isinstance(result, Exception):
            logger.warning("Finding validation raised: %s", result)
            continue
        if result is not None:
            validated.append(result)

    return validated
