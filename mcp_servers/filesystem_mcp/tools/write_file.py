"""MCP tool: write content to a file on the local filesystem.

Used by the developer agent to apply proposed fixes to files within
a repository checkout.
"""


async def write_file(path: str, content: str) -> dict:
    """Write the given content to the file at path."""
    pass
