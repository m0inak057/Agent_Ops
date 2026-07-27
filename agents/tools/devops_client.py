"""MCP client wrapper for connecting agents to the devops_mcp server.

Spawns the devops_mcp server over stdio and calls its tools (Dockerfile,
CI pipeline, and env file inspection) as agent-callable functions.
Callers that make several calls in a row should open one session via
devops_mcp_session() and pass it through, rather than spawning a fresh
subprocess per call.
"""

import json
import os
from contextlib import asynccontextmanager

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

DEVOPS_MCP_SERVER_PATH = "/app/mcp_servers/devops_mcp/server.py"


@asynccontextmanager
async def devops_mcp_session():
    """Open a single MCP session against the devops_mcp server."""
    server_params = StdioServerParameters(
        command="python",
        args=[DEVOPS_MCP_SERVER_PATH],
        env={**os.environ, "MCP_EPHEMERAL": "true"},
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


async def call_devops_tool(tool_name: str, arguments: dict, session=None) -> str:
    """Call a tool on the devops_mcp server, reusing a session if given."""
    if session is not None:
        result = await session.call_tool(tool_name, arguments)
        return result.content[0].text
    async with devops_mcp_session() as s:
        result = await s.call_tool(tool_name, arguments)
        return result.content[0].text


async def inspect_dockerfile(content: str, session=None) -> dict:
    """Analyze Dockerfile content for common misconfigurations."""
    result = await call_devops_tool("inspect_dockerfile", {"content": content}, session)
    return json.loads(result)


async def inspect_ci_pipeline(content: str, session=None) -> dict:
    """Analyze GitHub Actions workflow YAML content for missing steps."""
    result = await call_devops_tool(
        "inspect_ci_pipeline", {"content": content}, session
    )
    return json.loads(result)


async def check_env_files(file_content: str, session=None) -> dict:
    """Analyze .env or .env.example content for exposed secrets."""
    result = await call_devops_tool(
        "check_env_files", {"file_content": file_content}, session
    )
    return json.loads(result)
