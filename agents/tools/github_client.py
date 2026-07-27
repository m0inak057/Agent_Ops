"""Direct GitHub REST API client used by agents to read repository content.

Uses httpx for async HTTP calls against the GitHub REST API. This is a
stopgap until the github_mcp server is wired in (V2) — agents call these
functions directly instead of going through MCP.
"""

import base64
import os

import httpx

GITHUB_API_BASE = "https://api.github.com"


def _headers() -> dict:
    token = os.environ.get("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


async def get_repository(repo_name: str) -> dict:
    """GET /repos/{repo_name} — returns repo metadata."""
    url = f"{GITHUB_API_BASE}/repos/{repo_name}"
    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(url, headers=_headers())
    if response.status_code != 200:
        raise Exception(
            f"GitHub API error fetching repository {repo_name}: "
            f"{response.status_code} {response.text}"
        )
    return response.json()


async def get_repository_tree(repo_name: str) -> list[dict]:
    """GET /repos/{repo_name}/git/trees/HEAD?recursive=1

    Returns list of {path, type} for all files.
    """
    url = f"{GITHUB_API_BASE}/repos/{repo_name}/git/trees/HEAD"
    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(url, headers=_headers(), params={"recursive": "1"})
    if response.status_code != 200:
        raise Exception(
            f"GitHub API error fetching tree for {repo_name}: "
            f"{response.status_code} {response.text}"
        )
    data = response.json()
    return [{"path": item["path"], "type": item["type"]} for item in data.get("tree", [])]


async def get_file_content(repo_name: str, file_path: str) -> str:
    """GET /repos/{repo_name}/contents/{file_path}

    Returns decoded file content as string (base64 decode the response).
    """
    url = f"{GITHUB_API_BASE}/repos/{repo_name}/contents/{file_path}"
    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(url, headers=_headers())
    if response.status_code != 200:
        raise Exception(
            f"GitHub API error fetching file {file_path} in {repo_name}: "
            f"{response.status_code} {response.text}"
        )
    data = response.json()
    if data.get("encoding") != "base64" or "content" not in data:
        raise Exception(f"Unexpected content response for {file_path} in {repo_name}")
    return base64.b64decode(data["content"]).decode("utf-8", errors="replace")


async def search_code(repo_name: str, query: str) -> list[dict]:
    """GET /search/code?q={query}+repo:{repo_name}

    Returns list of {path, url} matches.
    """
    url = f"{GITHUB_API_BASE}/search/code"
    params = {"q": f"{query} repo:{repo_name}"}
    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(url, headers=_headers(), params=params)
    if response.status_code != 200:
        raise Exception(
            f"GitHub API error searching code in {repo_name}: "
            f"{response.status_code} {response.text}"
        )
    data = response.json()
    return [{"path": item["path"], "url": item["url"]} for item in data.get("items", [])]
