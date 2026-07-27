"""MCP server exposing test and static analysis execution as tools.

Registers tools for running the test suite, measuring coverage, and
running linters and security scanners. Runs the MCP stdio server plus
a /health HTTP endpoint on port 8003.
"""

import asyncio
import logging
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

logging.basicConfig(level=logging.INFO)

app = Server("test-mcp")

TIMEOUT_SECONDS = 60

TOOLS = [
    types.Tool(
        name="run_tests",
        description="Run pytest against the given path and return the output.",
        inputSchema={
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    ),
    types.Tool(
        name="run_coverage",
        description="Run pytest with coverage against the given path and return the report.",
        inputSchema={
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    ),
    types.Tool(
        name="run_linter",
        description="Run flake8 against the given path and return the lint output.",
        inputSchema={
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    ),
    types.Tool(
        name="run_bandit",
        description="Run bandit security scanning against the given path and return JSON output.",
        inputSchema={
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    ),
]


def _run_subprocess(command: list[str]) -> str:
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
        return (completed.stdout or "") + (completed.stderr or "")
    except subprocess.TimeoutExpired:
        return f"Error: command timed out after {TIMEOUT_SECONDS}s: {' '.join(command)}"
    except Exception as exc:
        return f"Error running command {' '.join(command)}: {exc}"


async def _run_tests(path: str) -> str:
    return _run_subprocess(["pytest", path, "--tb=short", "-q"])


async def _run_coverage(path: str) -> str:
    return _run_subprocess(["pytest", path, "--cov", "--cov-report=term-missing", "-q"])


async def _run_linter(path: str) -> str:
    return _run_subprocess(["flake8", path, "--max-line-length=100"])


async def _run_bandit(path: str) -> str:
    return _run_subprocess(["bandit", "-r", path, "-f", "json"])


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return TOOLS


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    try:
        if name == "run_tests":
            result = await _run_tests(arguments["path"])
        elif name == "run_coverage":
            result = await _run_coverage(arguments["path"])
        elif name == "run_linter":
            result = await _run_linter(arguments["path"])
        elif name == "run_bandit":
            result = await _run_bandit(arguments["path"])
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
    server = HTTPServer(("0.0.0.0", 8003), HealthHandler)
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
