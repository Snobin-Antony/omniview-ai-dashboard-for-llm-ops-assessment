"""Partial-failure reconciliation: blob exists while status is failed → completed."""
from __future__ import annotations

import uuid

import pytest

from app import blob_store
from app.db import SessionLocal
from app.models import Job, JobStatus, Provider
from app.seed import ORG_ID, WS_A_ID
from app.services import jobs as job_svc


@pytest.mark.asyncio(loop_scope="session")
async def test_reconcile_when_blob_exists_but_status_failed():
    job_id = uuid.uuid4()
    blob_store.write_blob(
        job_id,
        {"insights": {"summary": "recovered"}, "job_id": str(job_id)},
    )
    async with SessionLocal() as session:
        job = Job(
            id=job_id,
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

        fixed = await job_svc.get_job_reconciled(session, job_id, WS_A_ID)
        assert fixed is not None
        assert fixed.status == JobStatus.completed
        assert fixed.blob_url is not None
        assert fixed.error is None
