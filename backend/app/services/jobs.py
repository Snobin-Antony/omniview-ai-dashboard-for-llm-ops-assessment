from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import blob_store
from app.models import AnalysisStatus, Document, Job, JobStatus, Workspace
from app.redis_client import enqueue_job, get_job_status_cache, set_job_status_cache
from app.schemas import JobCreate

STALE_STATUSES = (JobStatus.failed, JobStatus.processing, JobStatus.dlq)


async def create_job(db: AsyncSession, payload: JobCreate, org_id: UUID) -> Job:
    job = Job(
        org_id=org_id,
        workspace_id=payload.workspace_id,
        document_id=payload.document_id,
        status=JobStatus.queued,
        provider=payload.provider,
        model=payload.model,
        workflow_name=payload.workflow_name,
    )
    db.add(job)
    if payload.document_id:
        doc = await db.get(Document, payload.document_id)
        if doc and doc.workspace_id == payload.workspace_id:
            doc.analysis_status = AnalysisStatus.queued
    await db.commit()
    await db.refresh(job)
    await enqueue_job(job.id)
    await set_job_status_cache(job.id, JobStatus.queued.value)
    return job


async def apply_blob_completion(db: AsyncSession, job: Job) -> bool:
    """If blob exists and job is not completed, mark completed. Returns True if changed."""
    if job.status == JobStatus.completed:
        return False
    if not blob_store.blob_exists(job.id):
        return False
    payload = blob_store.read_blob(job.id) or {}
    job.status = JobStatus.completed
    job.blob_url = str(blob_store.blob_path(job.id))
    job.error = None
    if job.document_id:
        doc = await db.get(Document, job.document_id)
        if doc:
            doc.analysis_status = AnalysisStatus.completed
            doc.insights = payload.get("insights") or payload
    await db.commit()
    await db.refresh(job)
    await set_job_status_cache(job.id, JobStatus.completed.value, {"reconciled": True})
    return True


async def get_job_reconciled(db: AsyncSession, job_id: UUID, workspace_id: UUID) -> Job | None:
    result = await db.execute(
        select(Job).where(Job.id == job_id, Job.workspace_id == workspace_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        return None

    await apply_blob_completion(db, job)

    cache = await get_job_status_cache(job.id)
    if cache and cache.get("status") != job.status.value:
        await set_job_status_cache(job.id, job.status.value)

    return job


async def retry_job(db: AsyncSession, job_id: UUID, workspace_id: UUID) -> Job | None:
    job = await get_job_reconciled(db, job_id, workspace_id)
    if not job:
        return None
    if job.status == JobStatus.completed:
        return job  # idempotent: return existing result

    job.status = JobStatus.queued
    job.error = None
    job.worker_id = None
    job.lease_expires_at = None
    job.retry_count = 0
    if job.document_id:
        doc = await db.get(Document, job.document_id)
        if doc:
            doc.analysis_status = AnalysisStatus.queued
    await db.commit()
    await db.refresh(job)
    await enqueue_job(job.id)
    await set_job_status_cache(job.id, JobStatus.queued.value)
    return job


async def list_jobs(db: AsyncSession, workspace_id: UUID, limit: int = 50) -> list[Job]:
    result = await db.execute(
        select(Job)
        .where(Job.workspace_id == workspace_id)
        .order_by(Job.created_at.desc())
        .limit(limit)
    )
    jobs = list(result.scalars().all())

    # UI polls this endpoint — heal false failures here, not only on GET-by-id.
    changed = False
    for job in jobs:
        if job.status in STALE_STATUSES and blob_store.blob_exists(job.id):
            if await apply_blob_completion(db, job):
                changed = True
    if changed:
        result = await db.execute(
            select(Job)
            .where(Job.workspace_id == workspace_id)
            .order_by(Job.created_at.desc())
            .limit(limit)
        )
        jobs = list(result.scalars().all())

    return jobs


async def workspace_org_id(db: AsyncSession, workspace_id: UUID) -> UUID | None:
    ws = await db.get(Workspace, workspace_id)
    return ws.org_id if ws else None
