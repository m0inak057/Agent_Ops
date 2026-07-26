"""API routes for retrieving findings produced by audit agents.

Exposes endpoints to list findings for an audit job and fetch the
detail of a specific finding, including its confidence and evidence.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/findings", tags=["findings"])


@router.get("/")
async def list_findings():
    """List findings, optionally filtered by audit job."""
    pass


@router.get("/{finding_id}")
async def get_finding(finding_id: str):
    """Retrieve a single finding by ID."""
    pass
