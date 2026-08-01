"""Unified audit agent.

Replaces the 7 specialist agents (security, code_quality, architecture,
performance, testing, devops, documentation) with a single LLM call that
analyzes the repo map across all 7 dimensions at once.
"""

from agents._llm_common import call_llm_for_findings

SYSTEM_PROMPT = """You are a senior software engineer conducting \
a comprehensive codebase audit. Analyze the provided repository \
information across ALL of these 7 dimensions simultaneously:

1. security - hardcoded secrets, injection risks, auth issues
2. code_quality - bugs, complexity, dead code, error handling
3. architecture - coupling, missing async, scalability risks
4. performance - N+1 queries, blocking I/O, missing indexes
5. testing - coverage gaps, missing tests on critical paths
6. devops - Docker security, missing CI/CD, secrets management
7. documentation - README quality, missing setup instructions

Return ONLY a JSON array of findings. No other text.
Each finding must have exactly these fields:
- category: one of the 7 dimensions above
- severity: critical, high, medium, or low
- title: short specific title
- detail: explanation with evidence and exact fix (min 50 chars)
- file_path: specific file path or null
- line_number: integer or null
- confidence: float 0.0-1.0
- auto_fix_available: boolean

Be specific and evidence-based. Only report issues you can
infer from the provided repository information.
Return 5-15 findings maximum. Quality over quantity."""


async def run_unified_audit(repo_map: dict) -> list[dict]:
    """Run a single LLM call covering all 7 audit dimensions.

    Replaces the 7 specialist agents. Returns findings across all
    categories in one response.
    """
    user_prompt = f"""Repository: {repo_map.get('project_type', 'Unknown')}
Languages: {', '.join(repo_map.get('languages', []))}
Has Dockerfile: {repo_map.get('has_dockerfile', False)}
Has CI/CD: {repo_map.get('has_ci_cd', False)}
Has Tests: {repo_map.get('has_tests', False)}
Has README: {repo_map.get('has_readme', False)}
Total Files: {repo_map.get('total_files', 0)}

File tree (first 80 files):
{repo_map.get('file_tree', [])[:80]}

Dependencies:
{str(repo_map.get('dependency_file_content', 'Not found'))[:3000]}

Dockerfile:
{str(repo_map.get('dockerfile_content', 'Not found'))[:1000]}

README (first 2000 chars):
{str(repo_map.get('readme_content', 'Not found'))[:2000]}

CI/CD Config:
{str(repo_map.get('ci_cd_content', 'Not found'))[:1000]}"""

    findings = await call_llm_for_findings(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
        agent_role="unified",
    )

    for finding in findings:
        finding["agent_role"] = finding.get("category") or "unified"

    return findings
