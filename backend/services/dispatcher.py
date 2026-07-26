"""Service responsible for dispatching audit jobs to the agent team.

Coordinates spawning the manager agent, tracking agent run lifecycle,
and persisting results back to the database.
"""


class Dispatcher:
    """Dispatches audit jobs to the agent team and tracks their lifecycle."""

    async def dispatch_audit(self, audit_job_id: str):
        """Kick off an audit job by invoking the agent manager."""
        pass
