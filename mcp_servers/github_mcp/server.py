"""MCP server exposing GitHub repository operations as tools.

Registers tools for reading a repository's metadata/tree/files,
searching code, and creating branches, commits, and pull requests.
Runs the MCP stdio server plus a /health HTTP endpoint on port 8001.
"""

import asyncio
import base64
import json
import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import httpx
import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

logging.basicConfig(level=logging.INFO)

GITHUB_API_BASE = "https://api.github.com"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}

app = Server("github-mcp")

TOOLS = [
    types.Tool(
        name="get_repository",
        description="Get metadata for a GitHub repository.",
        inputSchema={
            "type": "object",
            "properties": {"repo_name": {"type": "string"}},
            "required": ["repo_name"],
        },
    ),
    types.Tool(
        name="get_repository_tree",
        description="Get the full recursive file tree of a GitHub repository.",
        inputSchema={
            "type": "object",
            "properties": {"repo_name": {"type": "string"}},
            "required": ["repo_name"],
        },
    ),
    types.Tool(
        name="read_file",
        description="Read the decoded contents of a file in a GitHub repository.",
        inputSchema={
            "type": "object",
            "properties": {
                "repo_name": {"type": "string"},
                "file_path": {"type": "string"},
            },
            "required": ["repo_name", "file_path"],
        },
    ),
    types.Tool(
        name="search_code",
        description="Search for code matching a query within a GitHub repository.",
        inputSchema={
            "type": "object",
            "properties": {
                "repo_name": {"type": "string"},
                "query": {"type": "string"},
            },
            "required": ["repo_name", "query"],
        },
    ),
    types.Tool(
        name="create_branch",
        description="Create a new branch in a GitHub repository from an existing branch.",
        inputSchema={
            "type": "object",
            "properties": {
                "repo_name": {"type": "string"},
                "branch_name": {"type": "string"},
                "from_branch": {"type": "string"},
            },
            "required": ["repo_name", "branch_name", "from_branch"],
        },
    ),
    types.Tool(
        name="create_commit",
        description="Create or update a file on a branch, producing a new commit.",
        inputSchema={
            "type": "object",
            "properties": {
                "repo_name": {"type": "string"},
                "branch_name": {"type": "string"},
                "file_path": {"type": "string"},
                "content": {"type": "string"},
                "commit_message": {"type": "string"},
            },
            "required": [
                "repo_name",
                "branch_name",
                "file_path",
                "content",
                "commit_message",
            ],
        },
    ),
    types.Tool(
        name="create_pull_request",
        description="Create a pull request in a GitHub repository.",
        inputSchema={
            "type": "object",
            "properties": {
                "repo_name": {"type": "string"},
                "title": {"type": "string"},
                "body": {"type": "string"},
                "head_branch": {"type": "string"},
                "base_branch": {"type": "string"},
            },
            "required": ["repo_name", "title", "head_branch", "base_branch"],
        },
    ),
]


async def _get_repository(repo_name: str) -> str:
    url = f"{GITHUB_API_BASE}/repos/{repo_name}"
    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(url, headers=HEADERS)
    if response.status_code != 200:
        return f"Error fetching repository {repo_name}: {response.status_code} {response.text}"
    return json.dumps(response.json())


async def _get_repository_tree(repo_name: str) -> str:
    url = f"{GITHUB_API_BASE}/repos/{repo_name}/git/trees/HEAD"
    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(url, headers=HEADERS, params={"recursive": "1"})
    if response.status_code != 200:
        return f"Error fetching tree for {repo_name}: {response.status_code} {response.text}"
    data = response.json()
    tree = [{"path": item["path"], "type": item["type"]} for item in data.get("tree", [])]
    return json.dumps(tree)


async def _read_file(repo_name: str, file_path: str) -> str:
    url = f"{GITHUB_API_BASE}/repos/{repo_name}/contents/{file_path}"
    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(url, headers=HEADERS)
    if response.status_code != 200:
        return f"Error reading file {file_path} in {repo_name}: {response.status_code} {response.text}"
    data = response.json()
    if data.get("encoding") != "base64" or "content" not in data:
        return f"Unexpected content response for {file_path} in {repo_name}"
    return base64.b64decode(data["content"]).decode("utf-8", errors="replace")


async def _search_code(repo_name: str, query: str) -> str:
    url = f"{GITHUB_API_BASE}/search/code"
    params = {"q": f"{query} repo:{repo_name}"}
    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(url, headers=HEADERS, params=params)
    if response.status_code != 200:
        return f"Error searching code in {repo_name}: {response.status_code} {response.text}"
    data = response.json()
    matches = [{"path": item["path"], "url": item["url"]} for item in data.get("items", [])]
    return json.dumps(matches)


async def _create_branch(repo_name: str, branch_name: str, from_branch: str) -> str:
    async with httpx.AsyncClient(follow_redirects=True) as client:
        ref_url = f"{GITHUB_API_BASE}/repos/{repo_name}/git/ref/heads/{from_branch}"
        ref_response = await client.get(ref_url, headers=HEADERS)
        if ref_response.status_code != 200:
            return (
                f"Error resolving base branch {from_branch} in {repo_name}: "
                f"{ref_response.status_code} {ref_response.text}"
            )
        base_sha = ref_response.json()["object"]["sha"]

        create_url = f"{GITHUB_API_BASE}/repos/{repo_name}/git/refs"
        payload = {"ref": f"refs/heads/{branch_name}", "sha": base_sha}
        create_response = await client.post(create_url, headers=HEADERS, json=payload)
        if create_response.status_code not in (200, 201):
            return (
                f"Error creating branch {branch_name} in {repo_name}: "
                f"{create_response.status_code} {create_response.text}"
            )
    return f"Branch {branch_name} created successfully in {repo_name} from {from_branch}"


async def _create_commit(
    repo_name: str, branch_name: str, file_path: str, content: str, commit_message: str
) -> str:
    encoded_content = base64.b64encode(content.encode("utf-8")).decode("ascii")
    async with httpx.AsyncClient(follow_redirects=True) as client:
        contents_url = f"{GITHUB_API_BASE}/repos/{repo_name}/contents/{file_path}"
        existing_sha = None
        existing_response = await client.get(
            contents_url, headers=HEADERS, params={"ref": branch_name}
        )
        if existing_response.status_code == 200:
            existing_sha = existing_response.json().get("sha")

        payload = {
            "message": commit_message,
            "content": encoded_content,
            "branch": branch_name,
        }
        if existing_sha:
            payload["sha"] = existing_sha

        put_response = await client.put(contents_url, headers=HEADERS, json=payload)
        if put_response.status_code not in (200, 201):
            return (
                f"Error creating commit for {file_path} in {repo_name}: "
                f"{put_response.status_code} {put_response.text}"
            )
        commit_sha = put_response.json().get("commit", {}).get("sha", "")
    return commit_sha


async def _create_pull_request(
    repo_name: str, title: str, body: str, head_branch: str, base_branch: str
) -> str:
    url = f"{GITHUB_API_BASE}/repos/{repo_name}/pulls"
    payload = {
        "title": title,
        "body": body or "",
        "head": head_branch,
        "base": base_branch,
    }
    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.post(url, headers=HEADERS, json=payload)
    if response.status_code not in (200, 201):
        return (
            f"Error creating pull request in {repo_name}: "
            f"{response.status_code} {response.text}"
        )
    return response.json().get("html_url", "")


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return TOOLS


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    try:
        if name == "get_repository":
            result = await _get_repository(arguments["repo_name"])
        elif name == "get_repository_tree":
            result = await _get_repository_tree(arguments["repo_name"])
        elif name == "read_file":
            result = await _read_file(arguments["repo_name"], arguments["file_path"])
        elif name == "search_code":
            result = await _search_code(arguments["repo_name"], arguments["query"])
        elif name == "create_branch":
            result = await _create_branch(
                arguments["repo_name"], arguments["branch_name"], arguments["from_branch"]
            )
        elif name == "create_commit":
            result = await _create_commit(
                arguments["repo_name"],
                arguments["branch_name"],
                arguments["file_path"],
                arguments["content"],
                arguments["commit_message"],
            )
        elif name == "create_pull_request":
            result = await _create_pull_request(
                arguments["repo_name"],
                arguments["title"],
                arguments.get("body", ""),
                arguments["head_branch"],
                arguments["base_branch"],
            )
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
    server = HTTPServer(("0.0.0.0", 8001), HealthHandler)
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
