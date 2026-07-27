"""MCP server exposing local filesystem operations as tools.

Registers tools for reading, writing, listing, and searching files
within a sandboxed directory. Runs the MCP stdio server plus a
/health HTTP endpoint on port 8002.
"""

import asyncio
import fnmatch
import json
import logging
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

logging.basicConfig(level=logging.INFO)

SANDBOX_PATH = os.environ.get("FILESYSTEM_SANDBOX_PATH", "/sandbox")

app = Server("filesystem-mcp")

TOOLS = [
    types.Tool(
        name="read_file",
        description="Read the contents of a file inside the sandbox.",
        inputSchema={
            "type": "object",
            "properties": {"file_path": {"type": "string"}},
            "required": ["file_path"],
        },
    ),
    types.Tool(
        name="write_file",
        description="Write content to a file inside the sandbox, creating parent directories as needed.",
        inputSchema={
            "type": "object",
            "properties": {
                "file_path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["file_path", "content"],
        },
    ),
    types.Tool(
        name="list_directory",
        description="List the entries of a directory inside the sandbox.",
        inputSchema={
            "type": "object",
            "properties": {"dir_path": {"type": "string"}},
            "required": ["dir_path"],
        },
    ),
    types.Tool(
        name="search_files",
        description="Search for files matching a glob pattern under the sandbox.",
        inputSchema={
            "type": "object",
            "properties": {"pattern": {"type": "string"}},
            "required": ["pattern"],
        },
    ),
]


def _resolve_path(relative_path: str) -> Path:
    sandbox_root = Path(SANDBOX_PATH).resolve()
    candidate = (sandbox_root / relative_path.lstrip("/\\")).resolve()
    try:
        candidate.relative_to(sandbox_root)
    except ValueError:
        raise ValueError(f"Path escapes sandbox: {relative_path}")
    return candidate


async def _read_file(file_path: str) -> str:
    path = _resolve_path(file_path)
    if not path.is_file():
        return f"Error: file not found: {file_path}"
    return path.read_text(encoding="utf-8", errors="replace")


async def _write_file(file_path: str, content: str) -> str:
    path = _resolve_path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return f"File written successfully: {file_path}"


async def _list_directory(dir_path: str) -> str:
    path = _resolve_path(dir_path)
    if not path.is_dir():
        return json.dumps({"error": f"Not a directory: {dir_path}"})
    entries = sorted(entry.name for entry in path.iterdir())
    return json.dumps(entries)


async def _search_files(pattern: str) -> str:
    sandbox_root = Path(SANDBOX_PATH).resolve()
    matches = []
    for dirpath, _dirnames, filenames in os.walk(sandbox_root):
        for filename in filenames:
            if fnmatch.fnmatch(filename, pattern):
                full_path = Path(dirpath) / filename
                matches.append(str(full_path.relative_to(sandbox_root)))
    return json.dumps(sorted(matches))


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return TOOLS


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    try:
        if name == "read_file":
            result = await _read_file(arguments["file_path"])
        elif name == "write_file":
            result = await _write_file(arguments["file_path"], arguments["content"])
        elif name == "list_directory":
            result = await _list_directory(arguments["dir_path"])
        elif name == "search_files":
            result = await _search_files(arguments["pattern"])
        else:
            result = f"Unknown tool: {name}"
    except Exception as exc:
        result = f"Error executing tool {name}: {exc}"

    return [types.TextContent(type="text", text=result)]


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{"status": "ok"}')

    def log_message(self, format, *args):
        pass


def run_health_server():
    server = HTTPServer(("0.0.0.0", 8002), HealthHandler)
    server.serve_forever()


MCP_EPHEMERAL = os.environ.get("MCP_EPHEMERAL", "false").lower() == "true"


async def main():
    if MCP_EPHEMERAL:
        # Ephemeral mode: spawned per-call by an agent client. Exit cleanly
        # on EOF so the client's subprocess cleanup (which waits for this
        # process to exit) doesn't hang forever.
        try:
            async with stdio_server() as (read_stream, write_stream):
                await app.run(
                    read_stream, write_stream, app.create_initialization_options()
                )
        except Exception as e:
            sys.stderr.write(f"MCP session ended: {e}\n")
            sys.stderr.flush()
    else:
        # Container mode: no client attached to stdin, so a single session
        # would hit EOF immediately and exit. Loop so the container stays
        # alive and healthy, picking up a real session whenever one attaches.
        while True:
            try:
                async with stdio_server() as (read_stream, write_stream):
                    await app.run(
                        read_stream, write_stream, app.create_initialization_options()
                    )
            except Exception as e:
                sys.stderr.write(f"MCP session ended, restarting: {e}\n")
                sys.stderr.flush()
                await asyncio.sleep(1)


if __name__ == "__main__":
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()
    asyncio.run(main())
