"""Testing agent.

Audits the repository's test coverage and testing practices using an
LLM call over the repo map gathered by the repo analyzer.
"""

from agents._llm_common import call_llm_for_findings

SYSTEM_PROMPT = """You are a senior QA engineer auditing a GitHub repository for testing quality.
Analyze the provided repository information and identify testing issues.
You must respond with a JSON array of findings only. No other text.
Each finding must have: category (always "testing"), severity
(critical/high/medium/low), title, detail (include the specific
evidence and exact fix), file_path (or null), line_number (or null),
confidence (0.0-1.0), auto_fix_available (bool).
Focus on: test coverage gaps, missing tests on critical paths, no
testing framework detected, untested integrations."""


async def run_testing_audit(repo_map: dict) -> list[dict]:
    """Run the testing specialist agent over a repo map and return findings."""
    dependency_content = repo_map.get("dependency_file_content") or ""
    readme_content = repo_map.get("readme_content")

    user_prompt = f"""Repository: {repo_map.get('project_type')}
Has tests directory: {repo_map.get('has_tests')}
Files: {repo_map.get('file_tree', [])[:50]}
Dependencies: {dependency_content[:2000]}
Dockerfile: {repo_map.get('dockerfile_content') or 'Not found'}
README: {readme_content[:1000] if readme_content else 'Not found'}"""

    return await call_llm_for_findings(
        SYSTEM_PROMPT, user_prompt, agent_role="testing", category="testing"
    )
