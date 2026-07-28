"""LLM-as-a-judge scoring for overall audit quality.

Calls an LLM to rate the relevance, depth, coverage, and
actionability of an audit's findings as a whole, since these
dimensions are hard to measure deterministically.
"""

import json
import logging

from agents._llm_common import MODEL, client

logger = logging.getLogger(__name__)

JUDGE_SYSTEM_PROMPT = """You are an expert software engineering auditor evaluating \
the quality of an automated code review. Score each dimension from \
0.0 to 1.0. Respond with JSON only:
{
  "finding_relevance": float,
  "finding_depth": float,
  "coverage": float,
  "actionability": float,
  "reasoning": str
}"""

JUDGED_DIMENSIONS = ("finding_relevance", "finding_depth", "coverage", "actionability")


async def judge_audit_quality(
    audit_id: str, findings: list[dict], repo_map: dict
) -> list[dict]:
    """Use an LLM judge to score the overall quality of an audit's findings.

    Returns a list of metric dicts, one per judged dimension. Returns
    an empty list if the LLM call fails or its response can't be
    parsed.
    """
    try:
        summary = [
            {
                "title": f.get("title"),
                "severity": f.get("severity"),
                "category": f.get("category"),
            }
            for f in findings[:10]
        ]

        user_prompt = f"""Repository type: {repo_map.get('project_type')}
Number of findings: {len(findings)}
Findings summary:
{json.dumps(summary, indent=2)}

Note: This is an automated static analysis audit without access to full
source code — only repository structure, config files, and documentation
were analyzed. Score accordingly — penalize only if findings are
completely irrelevant, not if they lack deep code-level specificity.

Rate the quality of this automated audit."""

        response = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=500,
            temperature=0.1,
        )
        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            content = content.strip("`")
            if content.lower().startswith("json"):
                content = content[4:]
            content = content.strip()
        parsed = json.loads(content)
        reasoning = parsed.get("reasoning", "")

        return [
            {
                "metric": f"audit_quality_{dimension}",
                "score": float(parsed[dimension]),
                "feedback": reasoning,
            }
            for dimension in JUDGED_DIMENSIONS
            if dimension in parsed
        ]
    except Exception as e:
        logger.warning("LLM judge call failed for audit %s: %s", audit_id, e)
        return []
