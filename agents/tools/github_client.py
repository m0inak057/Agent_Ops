"""MCP client wrapper for connecting agents to the github_mcp server.

Spawns the github_mcp server over stdio and calls its tools (repository
metadata/tree/file reads, code search, branch/commit/PR creation) as
agent-callable functions. Callers that make several calls in a row
(e.g. repo_analyzer) should open one session via github_mcp_session()
and pass it through, rather than spawning a fresh subprocess per call.
"""

import json
import os
from contextlib import asynccontextmanager

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

GITHUB_MCP_SERVER_PATH = "/app/mcp_servers/github_mcp/server.py"


@asynccontextmanager
async def github_mcp_session():
    """Open a single MCP session against the github_mcp server."""
    server_params = StdioServerParameters(
        command="python",
        args=[GITHUB_MCP_SERVER_PATH],
        env={
            **os.environ,
            "GITHUB_TOKEN": os.environ.get("GITHUB_TOKEN", ""),
            "MCP_EPHEMERAL": "true",
        },
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


async def call_github_tool(tool_name: str, arguments: dict, session=None) -> str:
    """Call a tool on the github_mcp server, reusing a session if given."""
    if session is not None:
        result = await session.call_tool(tool_name, arguments)
        return result.content[0].text
    async with github_mcp_session() as s:
        result = await s.call_tool(tool_name, arguments)
        return result.content[0].text


async def get_repository(repo_name: str, session=None) -> dict:
    """Get metadata for a GitHub repository via the github_mcp server."""
    result = await call_github_tool("get_repository", {"repo_name": repo_name}, session)
    return json.loads(result)


async def get_repository_tree(repo_name: str, session=None) -> list:
    """Get the full recursive file tree of a GitHub repository."""
    result = await call_github_tool(
        "get_repository_tree", {"repo_name": repo_name}, session
    )
    return json.loads(result)


async def get_file_content(repo_name: str, file_path: str, session=None) -> str:
    """Get the decoded contents of a file in a GitHub repository."""
    return await call_github_tool(
        "read_file", {"repo_name": repo_name, "file_path": file_path}, session
    )


async def search_code(repo_name: str, query: str, session=None) -> list:
    """Search for code matching a query within a GitHub repository."""
    result = await call_github_tool(
        "search_code", {"repo_name": repo_name, "query": query}, session
    )
    return json.loads(result)


async def create_pull_request(
    repo_name: str,
    title: str,
    body: str,
    head_branch: str,
    base_branch: str,
    session=None,
) -> str:
    """Create a pull request in a GitHub repository."""
    return await call_github_tool(
        "create_pull_request",
        {
            "repo_name": repo_name,
            "title": title,
            "body": body,
            "head_branch": head_branch,
            "base_branch": base_branch,
        },
        session,
    )
