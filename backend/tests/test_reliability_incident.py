"""Worker reliability: list polling heals false failures; lease claim stays exclusive."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import and_, or_, update

from app import blob_store
from app.db import SessionLocal
from app.models import Job, JobStatus, Provider
from app.seed import ORG_ID, WS_A_ID
from app.services import jobs as job_svc


@pytest.mark.asyncio(loop_scope="session")
async def test_list_jobs_reconciles_failed_when_blob_exists():
    """UI poll uses list_jobs — must mark completed when blob is already stored."""
    async with SessionLocal() as session:
        job = Job(
            org_id=ORG_ID,
            workspace_id=WS_A_ID,
            status=JobStatus.failed,
            error="crashed after blob write",
            provider=Provider.openai,
            model="gpt-4o-mini",
            workflow_name="document_analysis",
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        job_id = job.id

    blob_store.write_blob(job_id, {"job_id": str(job_id), "insights": {"summary": "stored"}})

    async with SessionLocal() as session:
        listed = await job_svc.list_jobs(session, WS_A_ID)
        listed_job = next(j for j in listed if j.id == job_id)
        assert listed_job.status == JobStatus.completed
        assert listed_job.error is None
        assert listed_job.blob_url is not None


@pytest.mark.asyncio(loop_scope="session")
async def test_fresh_lease_blocks_second_worker_claim():
    now = datetime.now(timezone.utc)
    async with SessionLocal() as session:
        job = Job(
            org_id=ORG_ID,
            workspace_id=WS_A_ID,
            status=JobStatus.processing,
            worker_id="worker-slow",
            lease_expires_at=now - timedelta(seconds=5),
            provider=Provider.openai,
            model="gpt-4o-mini",
            workflow_name="document_analysis",
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        job_id = job.id

    async def claim(worker_id: str) -> str | None:
        now2 = datetime.now(timezone.utc)
        async with SessionLocal() as session:
            stmt = (
                update(Job)
                .where(
                    Job.id == job_id,
                    or_(
                        Job.status == JobStatus.queued,
                        Job.status == JobStatus.failed,
                        and_(
                            Job.status == JobStatus.processing,
                            Job.lease_expires_at.is_not(None),
                            Job.lease_expires_at < now2,
                        ),
                    ),
                )
                .values(
                    status=JobStatus.processing,
                    worker_id=worker_id,
                    lease_expires_at=now2 + timedelta(seconds=60),
                )
                .returning(Job)
            )
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            if row:
                await session.commit()
                return worker_id
            await session.rollback()
            return None

    first = await claim("w1")
    second = await claim("w2")
    assert first == "w1"
    assert second is None
