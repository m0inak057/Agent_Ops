"""Architecture agent.

Audits the repository's structural design using an LLM call over the
repo map gathered by the repo analyzer.
"""

from agents._llm_common import call_llm_for_findings

SYSTEM_PROMPT = """You are a senior software architect auditing a GitHub repository's design.
Analyze the provided repository information and identify architectural issues.
You must respond with a JSON array of findings only. No other text.
Each finding must have: category (always "architecture"), severity
(critical/high/medium/low), title, detail (include the specific
evidence and exact fix), file_path (or null), line_number (or null),
confidence (0.0-1.0), auto_fix_available (bool).
Focus on: tight coupling between components, missing abstractions or
over-engineering, synchronous operations where async is needed, poor
separation of concerns, scalability risks in the current design,
monolithic patterns that should be separated, missing queue/worker
patterns for heavy operations, direct database access from wrong
layers."""


async def run_architecture_audit(repo_map: dict) -> list[dict]:
    """Run the architecture specialist agent over a repo map and return findings."""
    dependency_content = repo_map.get("dependency_file_content") or ""
    readme_content = repo_map.get("readme_content")

    user_prompt = f"""Repository: {repo_map.get('project_type')}
Files: {repo_map.get('file_tree', [])[:50]}
Dependencies: {dependency_content[:2000]}
Dockerfile: {repo_map.get('dockerfile_content') or 'Not found'}
README: {readme_content[:1000] if readme_content else 'Not found'}"""

    return await call_llm_for_findings(
        SYSTEM_PROMPT, user_prompt, agent_role="architecture", category="architecture"
    )
