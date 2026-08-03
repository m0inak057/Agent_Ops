"""API routes for creating and managing codebase audit jobs.

Exposes endpoints to start a new audit against a repository, list
existing audit jobs, and fetch the status/result of a specific job.
"""

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import get_db
from backend.models import AuditJob, AuditJobStatus
from backend.schemas import (
    AuditJobCreate,
    AuditJobCreateResponse,
    AuditJobResponse,
    AuditTimelineResponse,
    extract_repo_name,
)
from backend.services.dispatcher import dispatch_audit
from backend.services.tracer import get_audit_timeline

router = APIRouter(prefix="/audits", tags=["audits"])


@router.post(
    "", response_model=AuditJobCreateResponse, status_code=status.HTTP_201_CREATED
)
async def create_audit(
    payload: AuditJobCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> AuditJobCreateResponse:
    """Create a new audit job for a repository and dispatch it for analysis."""
    try:
        repo_name = extract_repo_name(payload.repo_url)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    audit_job = AuditJob(
        repo_url=payload.repo_url,
        repo_name=repo_name,
        status=AuditJobStatus.PENDING,
    )
    db.add(audit_job)
    await db.commit()
    await db.refresh(audit_job)

    background_tasks.add_task(dispatch_audit, audit_job.id)

    return AuditJobCreateResponse(
        audit_id=audit_job.id,
        status=audit_job.status,
        repo_url=audit_job.repo_url,
        repo_name=audit_job.repo_name,
    )


@router.get("/{audit_id}", response_model=AuditJobResponse)
async def get_audit(
    audit_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> AuditJob:
    """Retrieve a single audit job's full details by ID."""
    audit_job = await db.get(AuditJob, audit_id)
    if audit_job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Audit job not found"
        )
    return audit_job


@router.get("", response_model=list[AuditJobResponse])
async def list_audits(
    status_filter: AuditJobStatus | None = Query(default=None, alias="status"),
    db: AsyncSession = Depends(get_db),
) -> list[AuditJob]:
    """List all audit jobs, most recently created first, optionally filtered by status."""
    stmt = select(AuditJob).order_by(AuditJob.created_at.desc())
    if status_filter is not None:
        stmt = stmt.where(AuditJob.status == status_filter)

    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{audit_id}/timeline", response_model=AuditTimelineResponse)
async def get_audit_timeline_endpoint(
    audit_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> AuditTimelineResponse:
    """Return the full observability timeline for an audit."""
    audit_job = await db.get(AuditJob, audit_id)
    if audit_job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Audit job not found"
        )

    timeline = await get_audit_timeline(audit_id, db)
    total_duration_ms = sum(span["duration_ms"] or 0 for span in timeline)

    return AuditTimelineResponse(
        audit_id=str(audit_id),
        repo_name=audit_job.repo_name,
        status=audit_job.status,
        total_duration_ms=total_duration_ms,
        spans=timeline,
    )
