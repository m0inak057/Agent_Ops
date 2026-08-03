"""Repo analyzer agent.

Performs the initial pass over a repository: fetches metadata, builds a
file tree, and reads key configuration/documentation files to inform the
rest of the audit team.
"""

import re

from agents.tools.devops_client import (
    devops_mcp_session,
    inspect_ci_pipeline,
    inspect_dockerfile,
)
from agents.tools.github_client import (
    get_file_content,
    get_repository,
    get_repository_tree,
    github_mcp_session,
)
from agents.tools.test_client import test_mcp_session

DEPENDENCY_CANDIDATES = ["requirements.txt", "package.json"]

# Checked in order first; if none of these exact paths exist, we fall back
# to scanning the whole tree for any file whose name starts with the
# relevant prefix (see _find_matching_path), so Dockerfiles/compose files
# tucked away in project-specific subdirectories are still found.
DOCKERFILE_PATTERNS = [
    "Dockerfile",
    "infrastructure/Dockerfile.backend",
    "infrastructure/Dockerfile",
    "docker/Dockerfile",
    "deploy/Dockerfile",
]
COMPOSE_PATTERNS = [
    "docker-compose.yml",
    "docker-compose.yaml",
    "infrastructure/docker-compose.yml",
    "deploy/docker-compose.yml",
]
README_CANDIDATES = ["README.md"]

LANGUAGE_EXTENSIONS = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".go": "Go",
    ".rb": "Ruby",
    ".java": "Java",
    ".rs": "Rust",
    ".php": "PHP",
    ".cs": "C#",
    ".cpp": "C++",
    ".c": "C",
    ".html": "HTML",
    ".css": "CSS",
}


def _extract_repo_name(repo_url: str) -> str:
    match = re.search(r"github\.com[:/]+([^/]+/[^/.]+)", repo_url)
    if match:
        return match.group(1)
    return repo_url.strip("/")


async def _read_if_exists(repo_name: str, path: str, session) -> str | None:
    try:
        return await get_file_content(repo_name, path, session)
    except Exception:
        return None


def _find_matching_path(
    file_tree: list[str], patterns: list[str], prefix: str
) -> str | None:
    """Find a file in the tree matching a known pattern, or a name prefix.

    Checks the exact known-location patterns first, then falls back to
    scanning the whole tree for any file whose name starts with the given
    prefix, so files in arbitrary subdirectories are still found.
    """
    for pattern in patterns:
        if pattern in file_tree:
            return pattern

    for path in file_tree:
        filename = path.split("/")[-1]
        if filename.startswith(prefix):
            return path

    return None


def _detect_project_type(dependency_content: str | None, languages: list[str]) -> str:
    if dependency_content:
        lower = dependency_content.lower()
        if '"django"' in lower or "django" in lower:
            if "react" in lower:
                return "Django + React"
            return "Django"
        if "fastapi" in lower:
            return "FastAPI"
        if "flask" in lower:
            return "Flask"
        if '"react"' in lower:
            return "React"
        if '"express"' in lower:
            return "Node.js (Express)"
    if "Python" in languages:
        return "Python"
    if "JavaScript" in languages or "TypeScript" in languages:
        return "Node.js"
    if languages:
        return languages[0]
    return "Unknown"


async def analyze_repository(repo_url: str) -> dict:
    """Analyze a GitHub repository and return a structured map."""
    repo_name = _extract_repo_name(repo_url)

    async with github_mcp_session() as session:
        await get_repository(repo_name, session)
        tree = await get_repository_tree(repo_name, session)

        file_tree = [item["path"] for item in tree if item["type"] == "blob"]

        languages: set[str] = set()
        for path in file_tree:
            for ext, lang in LANGUAGE_EXTENSIONS.items():
                if path.endswith(ext):
                    languages.add(lang)
                    break

        dockerfile_path = _find_matching_path(
            file_tree, DOCKERFILE_PATTERNS, "Dockerfile"
        )
        compose_path = _find_matching_path(
            file_tree, COMPOSE_PATTERNS, "docker-compose"
        )
        has_docker_compose = compose_path is not None
        has_readme = any(path in file_tree for path in README_CANDIDATES)
        has_tests = any(
            "/tests/" in f"/{path}" or "/test/" in f"/{path}" for path in file_tree
        )

        workflow_files = sorted(
            path
            for path in file_tree
            if path.startswith(".github/workflows/")
            and (path.endswith(".yml") or path.endswith(".yaml"))
        )
        has_ci_cd = bool(workflow_files)

        dependency_file_content = None
        for candidate in DEPENDENCY_CANDIDATES:
            if candidate in file_tree:
                dependency_file_content = await _read_if_exists(
                    repo_name, candidate, session
                )
                if dependency_file_content is not None:
                    break

        dockerfile_content = None
        if dockerfile_path:
            dockerfile_content = await _read_if_exists(
                repo_name, dockerfile_path, session
            )
        has_dockerfile = dockerfile_content is not None

        readme_content = None
        if has_readme:
            readme_content = await _read_if_exists(repo_name, "README.md", session)

        ci_cd_content = None
        if workflow_files:
            ci_cd_content = await _read_if_exists(repo_name, workflow_files[0], session)

    # DevOps MCP analysis — structural inspection of Dockerfile/CI config.
    # A failure to even start the session must not crash the audit, so the
    # whole block (not just the individual tool calls) is guarded.
    devops_findings: list[dict] = []
    try:
        async with devops_mcp_session() as devops_session:
            if dockerfile_content:
                try:
                    result = await inspect_dockerfile(
                        dockerfile_content, session=devops_session
                    )
                    if isinstance(result, dict):
                        devops_findings.extend(result.get("findings", []))
                except Exception as e:
                    print(f"devops_mcp dockerfile inspection failed: {e}")

            if ci_cd_content:
                try:
                    result = await inspect_ci_pipeline(
                        ci_cd_content, session=devops_session
                    )
                    if isinstance(result, dict):
                        devops_findings.extend(result.get("findings", []))
                except Exception as e:
                    print(f"devops_mcp CI inspection failed: {e}")
    except Exception as e:
        print(f"devops_mcp session failed to start: {e}")
        devops_findings = []

    # Test MCP analysis — lint check for Python projects.
    # Linting requires the repo's files on local disk (via filesystem_mcp),
    # which isn't available during a remote audit, so we only prove the
    # test_mcp connection works and note the limitation honestly.
    lint_output = None
    if "Python" in languages:
        try:
            async with test_mcp_session():
                lint_output = (
                    "Linter requires local file access — available in auto-fix mode"
                )
        except Exception as e:
            print(f"test_mcp linter failed: {e}")

    project_type = _detect_project_type(dependency_file_content, sorted(languages))

    return {
        "project_type": project_type,
        "languages": sorted(languages),
        "has_dockerfile": has_dockerfile,
        "has_docker_compose": has_docker_compose,
        "has_ci_cd": has_ci_cd,
        "has_tests": has_tests,
        "has_readme": has_readme,
        "total_files": len(file_tree),
        "dependency_file_content": dependency_file_content,
        "dockerfile_content": dockerfile_content,
        "readme_content": readme_content,
        "ci_cd_content": ci_cd_content,
        "file_tree": file_tree,
        "devops_tool_findings": devops_findings,
        # List of finding dicts from devops_mcp structural analysis
        "lint_output": lint_output,
    }
