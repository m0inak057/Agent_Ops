"""MCP tool: run the Trivy vulnerability scanner against the repository.

Executes Trivy to detect vulnerable dependencies and misconfigured
container images for the security agent to analyze.
"""


async def run_trivy(repository_path: str) -> dict:
    """Run Trivy for the given repository and return findings."""
    pass
