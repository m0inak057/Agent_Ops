"""Developer agent.

Consumes approved findings and proposes concrete code fixes,
including creating branches, commits, and pull requests via the
GitHub MCP tools.
"""


class DeveloperAgent:
    """Proposes and submits code fixes for approved findings."""

    def propose_fix(self, finding_id: str):
        """Generate a proposed code fix for the given finding."""
        pass
