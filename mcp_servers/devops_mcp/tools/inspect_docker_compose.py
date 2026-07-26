"""MCP tool: inspect a docker-compose file for misconfigurations.

Parses a docker-compose file and flags issues such as missing
health checks, exposed secrets, or insecure network settings.
"""


async def inspect_docker_compose(path: str) -> dict:
    """Inspect the docker-compose file at path and return findings."""
    pass
