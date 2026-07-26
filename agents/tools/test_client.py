"""Client wrapper for connecting agents to the test_mcp server.

Exposes convenience methods that call the test MCP server's tools
(run tests, coverage, linter, bandit, semgrep, trivy) as
agent-callable functions.
"""


class TestMCPClient:
    """Thin client for invoking test_mcp server tools from an agent."""

    async def run_tests(self, repository_path: str):
        """Call the run_tests MCP tool."""
        pass
