"""Repo analyzer agent.

Performs the initial pass over a repository: clones it, builds a
file tree, and identifies languages, frameworks, and entry points to
inform the rest of the audit team.
"""


class RepoAnalyzerAgent:
    """Performs initial repository structure and technology analysis."""

    def run(self, repository_url: str):
        """Analyze the repository structure and produce a summary for other agents."""
        pass
