"""MCP server exposing test and static analysis execution as tools.

Registers tools for running the test suite, measuring coverage, and
running linters and security scanners (bandit, semgrep, trivy).
Runs on port 8003.
"""


def create_server():
    """Construct and return the configured MCP server instance."""
    pass


if __name__ == "__main__":
    create_server()
