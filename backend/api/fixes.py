"""API routes for approving agent-proposed auto-fixes for findings.

Exposes an endpoint to approve an eligible finding's auto-fix, which
queues a background task to generate and submit the fix.
"""

import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import get_db
from backend.models import Finding, FindingFixStatus
from backend.schemas import FixApproveResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fixes", tags=["fixes"])

AUTO_FIX_CONFIDENCE_THRESHOLD = 0.95


async def _queue_auto_fix(finding_id: uuid.UUID) -> None:
    """Placeholder background task that will trigger the developer agent's auto-fix flow.

    TODO: Wire the developer agent's auto-fix pipeline here in V1 Week 2
    """
    logger.info("Auto-fix queued for finding %s", finding_id)


@router.post("/{finding_id}/approve", response_model=FixApproveResponse)
async def approve_fix(
    finding_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> FixApproveResponse:
    """Approve an eligible finding's auto-fix and queue it for generation."""
    finding = await db.get(Finding, finding_id)
    if finding is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")

    if not finding.auto_fix_available:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Auto-fix is not available for this finding",
        )

    if finding.confidence < AUTO_FIX_CONFIDENCE_THRESHOLD:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Finding confidence ({finding.confidence}) is below the required "
                f"auto-fix threshold ({AUTO_FIX_CONFIDENCE_THRESHOLD})"
            ),
        )

    finding.fix_status = FindingFixStatus.APPROVED
    await db.commit()

    background_tasks.add_task(_queue_auto_fix, finding_id)

    return FixApproveResponse(
        finding_id=finding_id,
        fix_status=finding.fix_status,
        message="Auto-fix queued",
    )
