"""Client wrapper for connecting agents to the github_mcp server.

Exposes convenience methods that call the GitHub MCP server's tools
(clone, tree, read, search, branch, commit, PR) as agent-callable
functions.
"""


class GitHubMCPClient:
    """Thin client for invoking github_mcp server tools from an agent."""

    async def clone_repository(self, repository_url: str):
        """Call the clone_repository MCP tool."""
        pass
