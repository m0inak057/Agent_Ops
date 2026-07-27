"""Security agent.

Audits the repository for vulnerabilities, insecure patterns, and
exposed credentials using an LLM call over the repo map gathered by the
repo analyzer.
"""

from agents._llm_common import call_llm_for_findings

SYSTEM_PROMPT = """You are a senior security engineer auditing a GitHub repository.
Analyze the provided repository information and identify security issues.
You must respond with a JSON array of findings only. No other text.
Each finding must have: category (always "security"), severity
(critical/high/medium/low), title, detail (include the specific
evidence and exact fix), file_path (or null), line_number (or null),
confidence (0.0-1.0), auto_fix_available (bool).
Focus on: hardcoded secrets, injection risks, auth issues,
insecure configs, exposed credentials."""


async def run_security_audit(repo_map: dict) -> list[dict]:
    """Run the security specialist agent over a repo map and return findings."""
    dependency_content = repo_map.get("dependency_file_content") or ""
    readme_content = repo_map.get("readme_content")

    user_prompt = f"""Repository: {repo_map.get('project_type')}
Files: {repo_map.get('file_tree', [])[:50]}
Dependencies: {dependency_content[:2000]}
Dockerfile: {repo_map.get('dockerfile_content') or 'Not found'}
README: {readme_content[:1000] if readme_content else 'Not found'}"""

    return await call_llm_for_findings(
        SYSTEM_PROMPT, user_prompt, agent_role="security", category="security"
    )
