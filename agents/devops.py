"""DevOps agent.

Audits the repository's infrastructure configuration using an LLM call
over the repo map gathered by the repo analyzer.
"""

from agents._llm_common import call_llm_for_findings

SYSTEM_PROMPT = """You are a senior DevOps engineer auditing a GitHub repository's infrastructure.
Analyze the provided repository information and identify DevOps issues.
You must respond with a JSON array of findings only. No other text.
Each finding must have: category (always "devops"), severity
(critical/high/medium/low), title, detail (include the specific
evidence and exact fix), file_path (or null), line_number (or null),
confidence (0.0-1.0), auto_fix_available (bool).
Focus on: Docker security, missing CI/CD, secrets in env files, no
health checks, container running as root, missing .dockerignore."""


async def run_devops_audit(repo_map: dict) -> list[dict]:
    """Run the devops specialist agent over a repo map and return findings."""
    dependency_content = repo_map.get("dependency_file_content") or ""
    readme_content = repo_map.get("readme_content")

    user_prompt = f"""Repository: {repo_map.get('project_type')}
Has Dockerfile: {repo_map.get('has_dockerfile')}
Has docker-compose: {repo_map.get('has_docker_compose')}
Has CI/CD: {repo_map.get('has_ci_cd')}
Files: {repo_map.get('file_tree', [])[:50]}
Dependencies: {dependency_content[:2000]}
Dockerfile: {repo_map.get('dockerfile_content') or 'Not found'}
CI/CD config: {repo_map.get('ci_cd_content') or 'Not found'}
README: {readme_content[:1000] if readme_content else 'Not found'}"""

    return await call_llm_for_findings(
        SYSTEM_PROMPT, user_prompt, agent_role="devops", category="devops"
    )
