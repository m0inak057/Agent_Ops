"""MCP tool: inspect a Dockerfile for misconfigurations.

Parses a Dockerfile and flags issues such as running as root,
missing health checks, or unpinned base images.
"""


async def inspect_dockerfile(path: str) -> dict:
    """Inspect the Dockerfile at path and return findings."""
    pass
