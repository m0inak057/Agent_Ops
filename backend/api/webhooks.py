"""GitHub webhook endpoint for continuous repository monitoring.

Receives GitHub push events, verifies their signature, and triggers
an automatic re-audit of the repository in the background.
"""

import hashlib
import hmac
import json
import os
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import get_db
from backend.models import AuditJob, AuditJobStatus
from backend.services.dispatcher import dispatch_audit

router = APIRouter()

WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")

RECENT_AUDIT_WINDOW = timedelta(minutes=5)


def verify_github_signature(payload: bytes, signature: str) -> bool:
    """Verify a GitHub webhook signature using HMAC-SHA256.

    GitHub sends: X-Hub-Signature-256: sha256=<hash>
    """
    if not WEBHOOK_SECRET:
        return True  # Skip verification if no secret configured

    expected = hmac.new(WEBHOOK_SECRET.encode(), payload, hashlib.sha256).hexdigest()

    return hmac.compare_digest(f"sha256={expected}", signature)


@router.post("/api/webhooks/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Receive GitHub webhook events.

    On push events to main/master, triggers an automatic re-audit of
    the repository.
    """
    body = await request.body()

    signature = request.headers.get("X-Hub-Signature-256", "")
    if not verify_github_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    event_type = request.headers.get("X-GitHub-Event", "")
    payload = json.loads(body)

    if event_type != "push":
        return {"message": f"Event {event_type} ignored"}

    repo_url = payload.get("repository", {}).get("html_url", "")
    repo_name = payload.get("repository", {}).get("full_name", "")
    pusher = payload.get("pusher", {}).get("name", "unknown")
    branch = payload.get("ref", "").replace("refs/heads/", "")

    if not repo_url:
        raise HTTPException(status_code=400, detail="No repository URL in payload")

    if branch not in ("main", "master"):
        return {
            "message": f"Push to {branch} ignored — only main/master triggers audit"
        }

    # Avoid duplicate audits from multiple rapid pushes to the same repo.
    recent_cutoff = datetime.utcnow() - RECENT_AUDIT_WINDOW
    recent_result = await db.execute(
        select(AuditJob)
        .where(
            and_(AuditJob.repo_url == repo_url, AuditJob.created_at >= recent_cutoff)
        )
        .limit(1)
    )
    recent_audit = recent_result.scalar_one_or_none()

    if recent_audit:
        return {
            "message": "Recent audit already exists for this repo",
            "audit_id": str(recent_audit.id),
            "status": recent_audit.status,
        }

    audit_job = AuditJob(
        id=uuid.uuid4(),
        repo_url=repo_url,
        repo_name=repo_name,
        status=AuditJobStatus.PENDING,
    )
    db.add(audit_job)
    await db.commit()
    await db.refresh(audit_job)

    background_tasks.add_task(dispatch_audit, audit_job.id)

    return {
        "message": f"Audit triggered for {repo_name} (push by {pusher} to {branch})",
        "audit_id": str(audit_job.id),
        "status": "pending",
    }


@router.get("/api/webhooks/health")
async def webhook_health():
    """Report webhook endpoint health, including whether a signing secret is configured."""
    return {"status": "ok", "webhook_secret_configured": bool(WEBHOOK_SECRET)}
