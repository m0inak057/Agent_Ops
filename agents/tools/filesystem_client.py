"""MCP client wrapper for connecting agents to the filesystem_mcp server.

Spawns the filesystem_mcp server over stdio and calls its tools (read,
write, list, search) within the sandboxed directory as agent-callable
functions. Callers that make several calls in a row should open one
session via filesystem_mcp_session() and pass it through, rather than
spawning a fresh subprocess per call.
"""

import json
import os
from contextlib import asynccontextmanager

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

FILESYSTEM_MCP_SERVER_PATH = "/app/mcp_servers/filesystem_mcp/server.py"


@asynccontextmanager
async def filesystem_mcp_session():
    """Open a single MCP session against the filesystem_mcp server."""
    server_params = StdioServerParameters(
        command="python",
        args=[FILESYSTEM_MCP_SERVER_PATH],
        env={
            **os.environ,
            "FILESYSTEM_SANDBOX_PATH": os.environ.get(
                "FILESYSTEM_SANDBOX_PATH", "/sandbox"
            ),
            "MCP_EPHEMERAL": "true",
        },
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


async def call_filesystem_tool(tool_name: str, arguments: dict, session=None) -> str:
    """Call a tool on the filesystem_mcp server, reusing a session if given."""
    if session is not None:
        result = await session.call_tool(tool_name, arguments)
        return result.content[0].text
    async with filesystem_mcp_session() as s:
        result = await s.call_tool(tool_name, arguments)
        return result.content[0].text


async def read_file(file_path: str, session=None) -> str:
    """Read the contents of a file inside the sandbox."""
    return await call_filesystem_tool("read_file", {"file_path": file_path}, session)


async def write_file(file_path: str, content: str, session=None) -> str:
    """Write content to a file inside the sandbox."""
    return await call_filesystem_tool(
        "write_file", {"file_path": file_path, "content": content}, session
    )


async def list_directory(dir_path: str, session=None) -> list:
    """List the entries of a directory inside the sandbox."""
    result = await call_filesystem_tool(
        "list_directory", {"dir_path": dir_path}, session
    )
    return json.loads(result)


async def search_files(pattern: str, session=None) -> list:
    """Search for files matching a glob pattern under the sandbox."""
    result = await call_filesystem_tool("search_files", {"pattern": pattern}, session)
    return json.loads(result)
