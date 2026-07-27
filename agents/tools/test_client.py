"""MCP client wrapper for connecting agents to the test_mcp server.

Spawns the test_mcp server over stdio and calls its tools (test
execution, coverage, linting, and bandit security scanning) as
agent-callable functions. Callers that make several calls in a row
should open one session via test_mcp_session() and pass it through,
rather than spawning a fresh subprocess per call.
"""

import os
from contextlib import asynccontextmanager

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

TEST_MCP_SERVER_PATH = "/app/mcp_servers/test_mcp/server.py"


@asynccontextmanager
async def test_mcp_session():
    """Open a single MCP session against the test_mcp server."""
    server_params = StdioServerParameters(
        command="python",
        args=[TEST_MCP_SERVER_PATH],
        env={**os.environ, "MCP_EPHEMERAL": "true"},
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


async def call_test_tool(tool_name: str, arguments: dict, session=None) -> str:
    """Call a tool on the test_mcp server, reusing a session if given."""
    if session is not None:
        result = await session.call_tool(tool_name, arguments)
        return result.content[0].text
    async with test_mcp_session() as s:
        result = await s.call_tool(tool_name, arguments)
        return result.content[0].text


async def run_tests(path: str, session=None) -> str:
    """Run pytest against the given path and return the output."""
    return await call_test_tool("run_tests", {"path": path}, session)


async def run_coverage(path: str, session=None) -> str:
    """Run pytest with coverage against the given path and return the report."""
    return await call_test_tool("run_coverage", {"path": path}, session)


async def run_linter(path: str, session=None) -> str:
    """Run flake8 against the given path and return the lint output."""
    return await call_test_tool("run_linter", {"path": path}, session)


async def run_bandit(path: str, session=None) -> str:
    """Run bandit security scanning against the given path and return JSON output."""
    return await call_test_tool("run_bandit", {"path": path}, session)
