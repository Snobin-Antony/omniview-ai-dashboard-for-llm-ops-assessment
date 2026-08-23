"""Backend tests: tenancy, retry idempotency, rollup accuracy, concurrency claim."""
from __future__ import annotations

import asyncio
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import and_, or_, update

from app.config import get_settings
from app.db import SessionLocal
from app.main import app
from app.models import Job, JobStatus, LlmUsageEvent, Provider, UsageStatus, Workspace
from app.seed import ADMIN_ID, ORG_ID, OWNER_ID, WS_A_ID, WS_B_ID
from app.services import jobs as job_svc
from app.services import usage as usage_svc


@pytest_asyncio.fixture(loop_scope="session")
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio(loop_scope="session")
async def test_workspace_admin_cannot_read_other_workspace_usage(client: AsyncClient):
    res = await client.get(
        f"/api/v1/workspaces/{WS_B_ID}/analytics/usage",
        headers={"X-User-Id": str(ADMIN_ID)},
    )
    assert res.status_code == 403


@pytest.mark.asyncio(loop_scope="session")
async def test_workspace_admin_can_read_own_workspace_usage(client: AsyncClient):
    res = await client.get(
        f"/api/v1/workspaces/{WS_A_ID}/analytics/usage",
        headers={"X-User-Id": str(ADMIN_ID)},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["workspace_id"] == str(WS_A_ID)


@pytest.mark.asyncio(loop_scope="session")
async def test_org_owner_can_access_org_usage(client: AsyncClient):
    res = await client.get(
        f"/api/v1/orgs/{ORG_ID}/analytics/usage",
        headers={"X-User-Id": str(OWNER_ID)},
    )
    assert res.status_code == 200
    assert "workspaces" in res.json()


@pytest.mark.asyncio(loop_scope="session")
async def test_workspace_admin_cannot_access_org_route(client: AsyncClient):
    res = await client.get(
        f"/api/v1/orgs/{ORG_ID}/analytics/usage",
        headers={"X-User-Id": str(ADMIN_ID)},
    )
    assert res.status_code == 403


@pytest.mark.asyncio(loop_scope="session")
async def test_retry_returns_existing_when_completed():
    async with SessionLocal() as session:
        job = Job(
            org_id=ORG_ID,
            workspace_id=WS_A_ID,
            status=JobStatus.completed,
            blob_url="/tmp/done.json",
            provider=Provider.openai,
            model="gpt-4o-mini",
            workflow_name="document_analysis",
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        job_id = job.id

        retried = await job_svc.retry_job(session, job_id, WS_A_ID)
        assert retried is not None
        assert retried.status == JobStatus.completed
        assert retried.id == job_id


@pytest.mark.asyncio(loop_scope="session")
async def test_rollup_matches_hand_calculated_events():
    async with SessionLocal() as session:
        ws = Workspace(org_id=ORG_ID, name=f"test-ws-{uuid.uuid4().hex[:6]}")
        session.add(ws)
        await session.flush()

        session.add_all(
            [
                LlmUsageEvent(
                    org_id=ORG_ID,
                    workspace_id=ws.id,
                    provider=Provider.openai,
                    model="gpt-4o-mini",
                    tokens_prompt=1000,
                    tokens_completion=1000,
                    cost_usd=Decimal("0.010000"),
                    status=UsageStatus.success,
                    workflow_name="t",
                ),
                LlmUsageEvent(
                    org_id=ORG_ID,
                    workspace_id=ws.id,
                    provider=Provider.openai,
                    model="gpt-4o-mini",
                    tokens_prompt=0,
                    tokens_completion=0,
                    cost_usd=Decimal("0"),
                    status=UsageStatus.failed,
                    workflow_name="t",
                    error_code="x",
                ),
            ]
        )
        await session.commit()
        await usage_svc.refresh_usage_rollups(session)

        today = date.today()
        summary = await usage_svc.get_workspace_usage(session, ws.id, today, today)
        assert summary.total_requests == 2
        assert summary.failed_request_count == 1
        assert summary.daily_spend == Decimal("0.010000")


@pytest.mark.asyncio(loop_scope="session")
async def test_duplicate_claim_only_one_wins():
    async with SessionLocal() as session:
        job = Job(
            org_id=ORG_ID,
            workspace_id=WS_A_ID,
            status=JobStatus.queued,
            provider=Provider.openai,
            model="gpt-4o-mini",
            workflow_name="document_analysis",
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        job_id = job.id

    async def claim(worker_id: str) -> Job | None:
        settings = get_settings()
        now = datetime.now(timezone.utc)
        async with SessionLocal() as session:
            stmt = (
                update(Job)
                .where(
                    Job.id == job_id,
                    or_(
                        Job.status == JobStatus.queued,
                        and_(
                            Job.status == JobStatus.processing,
                            Job.lease_expires_at.is_not(None),
                            Job.lease_expires_at < now,
                        ),
                    ),
                )
                .values(
                    status=JobStatus.processing,
                    worker_id=worker_id,
                    lease_expires_at=now + timedelta(seconds=settings.lease_seconds),
                )
                .returning(Job)
            )
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            if row:
                await session.commit()
            else:
                await session.rollback()
            return row

    first, second = await asyncio.gather(claim("w1"), claim("w2"))
    winners = [j for j in (first, second) if j is not None]
    assert len(winners) == 1
