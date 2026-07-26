"""API routes for creating and managing codebase audit jobs.

Exposes endpoints to start a new audit against a repository, list
existing audit jobs, and fetch the status/result of a specific job.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/audits", tags=["audits"])


@router.post("/")
async def create_audit():
    """Create and dispatch a new audit job for a repository."""
    pass


@router.get("/")
async def list_audits():
    """List all audit jobs."""
    pass


@router.get("/{audit_id}")
async def get_audit(audit_id: str):
    """Retrieve a single audit job by ID."""
    pass
