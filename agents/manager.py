"""Manager agent that orchestrates the audit workflow.

Plans the audit, delegates tasks to specialist agents, aggregates
their findings, and decides when the audit is complete.
"""


class ManagerAgent:
    """Orchestrates the audit workflow across all specialist agents."""

    def run(self, repository_url: str):
        """Plan and coordinate a full audit of the given repository."""
        pass
