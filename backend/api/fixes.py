"""API routes for managing agent-proposed code fixes.

Exposes endpoints to request a fix for a finding, review a proposed
fix, and approve/submit it as a pull request.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/fixes", tags=["fixes"])


@router.post("/{finding_id}")
async def request_fix(finding_id: str):
    """Request the developer agent to propose a fix for a finding."""
    pass


@router.get("/{fix_id}")
async def get_fix(fix_id: str):
    """Retrieve a proposed fix by ID."""
    pass


@router.post("/{fix_id}/approve")
async def approve_fix(fix_id: str):
    """Approve a proposed fix and submit it as a pull request."""
    pass
