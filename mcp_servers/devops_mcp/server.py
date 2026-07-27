"""MCP server exposing infrastructure inspection operations as tools.

Registers tools for inspecting Dockerfile content, CI pipeline YAML,
and .env file content for common misconfigurations. Runs the MCP
stdio server plus a /health HTTP endpoint on port 8004.
"""

import asyncio
import json
import logging
import re
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

logging.basicConfig(level=logging.INFO)

app = Server("devops-mcp")

TOOLS = [
    types.Tool(
        name="inspect_dockerfile",
        description="Analyze Dockerfile content for common misconfigurations.",
        inputSchema={
            "type": "object",
            "properties": {"content": {"type": "string"}},
            "required": ["content"],
        },
    ),
    types.Tool(
        name="inspect_ci_pipeline",
        description="Analyze GitHub Actions workflow YAML content for missing tests/lint/build steps.",
        inputSchema={
            "type": "object",
            "properties": {"content": {"type": "string"}},
            "required": ["content"],
        },
    ),
    types.Tool(
        name="check_env_files",
        description="Analyze .env or .env.example content for exposed secrets.",
        inputSchema={
            "type": "object",
            "properties": {"file_content": {"type": "string"}},
            "required": ["file_content"],
        },
    ),
]


async def _inspect_dockerfile(content: str) -> str:
    findings = []

    if not re.search(r"^\s*USER\s+\S+", content, re.MULTILINE):
        findings.append(
            {
                "issue": "missing_user_directive",
                "severity": "high",
                "detail": "No USER directive found; container will run as root.",
            }
        )

    if not re.search(r"^\s*HEALTHCHECK\b", content, re.MULTILINE):
        findings.append(
            {
                "issue": "missing_healthcheck",
                "severity": "low",
                "detail": "No HEALTHCHECK instruction found.",
            }
        )

    if re.search(r"^\s*FROM\s+\S+:latest\b", content, re.MULTILINE) or re.search(
        r"^\s*FROM\s+[^:\s]+\s*$", content, re.MULTILINE
    ):
        findings.append(
            {
                "issue": "unpinned_base_image",
                "severity": "medium",
                "detail": "Base image uses the 'latest' tag or no tag at all; pin to a specific version.",
            }
        )

    return json.dumps({"findings": findings})


async def _inspect_ci_pipeline(content: str) -> str:
    findings = []
    lower = content.lower()

    if not re.search(r"\bpytest\b|\bnpm\s+test\b|\byarn\s+test\b|\btest\b", lower):
        findings.append(
            {
                "issue": "no_tests_run",
                "severity": "high",
                "detail": "No test execution step detected in the CI pipeline.",
            }
        )

    if not re.search(r"\bflake8\b|\bruff\b|\beslint\b|\bpylint\b|\blint\b", lower):
        findings.append(
            {
                "issue": "no_linting",
                "severity": "medium",
                "detail": "No linting step detected in the CI pipeline.",
            }
        )

    if not re.search(r"docker\s+build|docker/build-push-action", lower):
        findings.append(
            {
                "issue": "no_docker_build",
                "severity": "low",
                "detail": "No Docker build step detected in the CI pipeline.",
            }
        )

    return json.dumps({"findings": findings})


PLACEHOLDER_PATTERN = re.compile(
    r"^(changeme|placeholder|your[_-].*|example|xxx+|<.*>|todo|replace[_-]?me|password|secret)$",
    re.IGNORECASE,
)
SECRET_LOOKING_PATTERN = re.compile(r"^[A-Za-z0-9/+_\-]{20,}$")


async def _check_env_files(file_content: str) -> str:
    findings = []

    for line_number, line in enumerate(file_content.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if not value:
            continue

        if PLACEHOLDER_PATTERN.match(value):
            continue

        if SECRET_LOOKING_PATTERN.match(value):
            findings.append(
                {
                    "issue": "possible_real_secret",
                    "severity": "critical",
                    "detail": f"Line {line_number}: '{key}' looks like a real secret value, not a placeholder.",
                }
            )

    return json.dumps({"findings": findings})


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return TOOLS


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    try:
        if name == "inspect_dockerfile":
            result = await _inspect_dockerfile(arguments["content"])
        elif name == "inspect_ci_pipeline":
            result = await _inspect_ci_pipeline(arguments["content"])
        elif name == "check_env_files":
            result = await _check_env_files(arguments["file_content"])
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
    server = HTTPServer(("0.0.0.0", 8004), HealthHandler)
    server.serve_forever()


async def main():
    # When run as a detached container (no client attached to stdin), stdin
    # hits EOF immediately and a single stdio_server session would return
    # right away, exiting the process. Loop so the container stays alive
    # and healthy, and picks up a real session whenever a client attaches.
    while True:
        try:
            async with stdio_server() as (read_stream, write_stream):
                await app.run(read_stream, write_stream, app.create_initialization_options())
        except Exception:
            logging.exception("MCP stdio session ended unexpectedly")
        await asyncio.sleep(1)


if __name__ == "__main__":
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()
    asyncio.run(main())
