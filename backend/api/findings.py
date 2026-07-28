"""API routes for retrieving findings produced by audit agents.

Exposes endpoints to list findings for an audit job, filterable by
severity and category, and a severity/category breakdown summary.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import get_db
from backend.models import AuditJob, Finding, FindingCategory, FindingSeverity
from backend.schemas import FindingResponse, FindingSummaryResponse

router = APIRouter(prefix="/findings", tags=["findings"])

_SEVERITY_ORDER = [
    FindingSeverity.CRITICAL,
    FindingSeverity.HIGH,
    FindingSeverity.MEDIUM,
    FindingSeverity.LOW,
]


async def _get_audit_or_404(audit_id: uuid.UUID, db: AsyncSession) -> AuditJob:
    """Fetch an AuditJob by ID or raise 404 if it does not exist."""
    audit_job = await db.get(AuditJob, audit_id)
    if audit_job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Audit job not found"
        )
    return audit_job


@router.get("/{audit_id}", response_model=list[FindingResponse])
async def list_findings(
    audit_id: uuid.UUID,
    severity: FindingSeverity | None = Query(default=None),
    category: FindingCategory | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> list[Finding]:
    """List findings for an audit, ordered by severity (critical first) then confidence."""
    await _get_audit_or_404(audit_id, db)

    severity_rank = case(
        *[(Finding.severity == sev, rank) for rank, sev in enumerate(_SEVERITY_ORDER)],
        else_=len(_SEVERITY_ORDER),
    )

    stmt = select(Finding).where(Finding.audit_id == audit_id)
    if severity is not None:
        stmt = stmt.where(Finding.severity == severity)
    if category is not None:
        stmt = stmt.where(Finding.category == category)

    stmt = stmt.order_by(severity_rank, Finding.confidence.desc())

    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{audit_id}/summary", response_model=FindingSummaryResponse)
async def findings_summary(
    audit_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> FindingSummaryResponse:
    """Return finding counts grouped by severity and by category for an audit."""
    await _get_audit_or_404(audit_id, db)

    severity_counts = dict.fromkeys(FindingSeverity, 0)
    severity_stmt = (
        select(Finding.severity, func.count())
        .where(Finding.audit_id == audit_id)
        .group_by(Finding.severity)
    )
    severity_result = await db.execute(severity_stmt)
    for severity_value, count in severity_result.all():
        severity_counts[FindingSeverity(severity_value)] = count

    category_counts = dict.fromkeys(FindingCategory, 0)
    category_stmt = (
        select(Finding.category, func.count())
        .where(Finding.audit_id == audit_id)
        .group_by(Finding.category)
    )
    category_result = await db.execute(category_stmt)
    for category_value, count in category_result.all():
        category_counts[FindingCategory(category_value)] = count

    return FindingSummaryResponse(
        critical=severity_counts[FindingSeverity.CRITICAL],
        high=severity_counts[FindingSeverity.HIGH],
        medium=severity_counts[FindingSeverity.MEDIUM],
        low=severity_counts[FindingSeverity.LOW],
        by_category={
            category.value: count for category, count in category_counts.items()
        },
    )
