"""Repo analyzer agent.

Performs the initial pass over a repository: fetches metadata, builds a
file tree, and reads key configuration/documentation files to inform the
rest of the audit team.
"""

import re

from agents.tools.github_client import (
    get_file_content,
    get_repository,
    get_repository_tree,
)

DEPENDENCY_CANDIDATES = ["requirements.txt", "package.json"]
DOCKERFILE_CANDIDATES = ["Dockerfile"]
COMPOSE_CANDIDATES = ["docker-compose.yml"]
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


async def _read_if_exists(repo_name: str, path: str) -> str | None:
    try:
        return await get_file_content(repo_name, path)
    except Exception:
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

    await get_repository(repo_name)
    tree = await get_repository_tree(repo_name)

    file_tree = [item["path"] for item in tree if item["type"] == "blob"]

    languages: set[str] = set()
    for path in file_tree:
        for ext, lang in LANGUAGE_EXTENSIONS.items():
            if path.endswith(ext):
                languages.add(lang)
                break

    has_dockerfile = any(path in file_tree for path in DOCKERFILE_CANDIDATES)
    has_docker_compose = any(path in file_tree for path in COMPOSE_CANDIDATES)
    has_readme = any(path in file_tree for path in README_CANDIDATES)
    has_tests = any(
        "/tests/" in f"/{path}" or "/test/" in f"/{path}" for path in file_tree
    )

    workflow_files = sorted(
        path
        for path in file_tree
        if path.startswith(".github/workflows/") and (path.endswith(".yml") or path.endswith(".yaml"))
    )
    has_ci_cd = bool(workflow_files)

    dependency_file_content = None
    for candidate in DEPENDENCY_CANDIDATES:
        if candidate in file_tree:
            dependency_file_content = await _read_if_exists(repo_name, candidate)
            if dependency_file_content is not None:
                break

    dockerfile_content = None
    if has_dockerfile:
        dockerfile_content = await _read_if_exists(repo_name, "Dockerfile")

    readme_content = None
    if has_readme:
        readme_content = await _read_if_exists(repo_name, "README.md")

    ci_cd_content = None
    if workflow_files:
        ci_cd_content = await _read_if_exists(repo_name, workflow_files[0])

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
    }
