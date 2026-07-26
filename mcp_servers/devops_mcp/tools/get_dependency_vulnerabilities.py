"""MCP tool: check project dependencies for known vulnerabilities.

Inspects dependency manifests (requirements.txt, package.json, etc.)
and reports known CVEs affecting pinned versions.
"""


async def get_dependency_vulnerabilities(repository_path: str) -> dict:
    """Check the repository's dependencies for known vulnerabilities."""
    pass
