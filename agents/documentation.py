"""Documentation agent.

Audits the repository's documentation quality using an LLM call over
the repo map gathered by the repo analyzer.
"""

from agents._llm_common import call_llm_for_findings

SYSTEM_PROMPT = """You are a senior technical writer auditing a GitHub repository's documentation.
Analyze the provided repository information and identify documentation issues.
You must respond with a JSON array of findings only. No other text.
Each finding must have: category (always "documentation"), severity
(critical/high/medium/low), title, detail (include the specific
evidence and exact fix), file_path (or null), line_number (or null),
confidence (0.0-1.0), auto_fix_available (bool).
Focus on: missing or incomplete README, no setup/installation
instructions, undocumented environment variables, missing API
documentation, no contributing guidelines, outdated documentation,
missing architecture overview, no examples or usage guides."""


async def run_documentation_audit(repo_map: dict) -> list[dict]:
    """Run the documentation specialist agent over a repo map and return findings."""
    dependency_content = repo_map.get("dependency_file_content") or ""
    readme_content = repo_map.get("readme_content")

    user_prompt = f"""Repository: {repo_map.get('project_type')}
Files: {repo_map.get('file_tree', [])[:50]}
Dependencies: {dependency_content[:2000]}
README: {readme_content[:2000] if readme_content else 'Not found'}"""

    return await call_llm_for_findings(
        SYSTEM_PROMPT, user_prompt, agent_role="documentation", category="documentation"
    )
