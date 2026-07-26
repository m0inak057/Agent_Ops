"""API routes for the evaluation subsystem.

Exposes an endpoint to retrieve evaluation metrics recorded for an
audit job.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import get_db
from backend.models import AuditJob, Evaluation
from backend.schemas import EvaluationResponse

router = APIRouter(prefix="/evaluations", tags=["evaluations"])


@router.get("/{audit_id}", response_model=list[EvaluationResponse])
async def list_evaluations(
    audit_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> list[Evaluation]:
    """Fetch all evaluation metrics recorded for an audit job."""
    audit_job = await db.get(AuditJob, audit_id)
    if audit_job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit job not found")

    stmt = (
        select(Evaluation)
        .where(Evaluation.audit_id == audit_id)
        .order_by(Evaluation.evaluated_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
