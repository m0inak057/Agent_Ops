"""Client wrapper for connecting agents to the filesystem_mcp server.

Exposes convenience methods that call the filesystem MCP server's
tools (read, write, list, search) as agent-callable functions.
"""


class FilesystemMCPClient:
    """Thin client for invoking filesystem_mcp server tools from an agent."""

    async def read_file(self, path: str):
        """Call the read_file MCP tool."""
        pass
