"""MCP tool: open a pull request on GitHub for a pushed branch.

Used by the developer agent to submit a proposed fix for human
review once its branch and commits are ready.
"""


async def create_pull_request(repository_url: str, branch_name: str, title: str, body: str) -> dict:
    """Open a pull request from the given branch against the default branch."""
    pass
