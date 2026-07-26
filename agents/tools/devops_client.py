"""Client wrapper for connecting agents to the devops_mcp server.

Exposes convenience methods that call the devops MCP server's tools
(Dockerfile, compose, CI pipeline, env file, dependency vulnerability
inspection) as agent-callable functions.
"""


class DevOpsMCPClient:
    """Thin client for invoking devops_mcp server tools from an agent."""

    async def inspect_dockerfile(self, path: str):
        """Call the inspect_dockerfile MCP tool."""
        pass
