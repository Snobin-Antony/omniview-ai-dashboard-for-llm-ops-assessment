"""Async job worker: lease claim, mock LLM, blob write, usage events, DLQ."""
from __future__ import annotations

import asyncio
import os
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

# Allow importing backend.app when run from repo root or worker/
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app import blob_store
from app.config import get_settings
from app.db import SessionLocal
from app.models import (
    AnalysisStatus,
    Document,
    Job,
    JobStatus,
    LlmUsageEvent,
    PricingRate,
    UsageStatus,
)
from app.redis_client import get_redis, move_to_dlq, set_job_status_cache

WORKER_ID = f"worker-{uuid.uuid4().hex[:8]}"


async def claim_job(session: AsyncSession, job_id: uuid.UUID) -> Job | None:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    lease_until = now + timedelta(seconds=settings.lease_seconds)

    # Never steal a completed job. Claim queued, failed (retry), or expired processing lease.
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
                    Job.lease_expires_at < now,
                ),
            ),
        )
        .values(
            status=JobStatus.processing,
            worker_id=WORKER_ID,
            lease_expires_at=lease_until,
        )
        .returning(Job)
    )
    result = await session.execute(stmt)
    job = result.scalar_one_or_none()
    if job:
        await session.commit()
        await session.refresh(job)
    else:
        await session.rollback()
    return job


async def compute_cost(
    session: AsyncSession, provider, model: str, prompt_tokens: int, completion_tokens: int
) -> Decimal:
    result = await session.execute(
        select(PricingRate).where(PricingRate.provider == provider, PricingRate.model == model)
    )
    rate = result.scalar_one_or_none()
    if not rate:
        return Decimal("0")
    cost = (Decimal(prompt_tokens) / 1000) * rate.prompt_per_1k + (
        Decimal(completion_tokens) / 1000
    ) * rate.completion_per_1k
    return cost.quantize(Decimal("0.000001"))


async def _has_success_usage(session: AsyncSession, job_id: uuid.UUID) -> bool:
    result = await session.execute(
        select(LlmUsageEvent.id).where(
            LlmUsageEvent.job_id == job_id,
            LlmUsageEvent.status == UsageStatus.success,
        )
    )
    return result.scalar_one_or_none() is not None


async def complete_from_blob(session: AsyncSession, job: Job, insights: dict | None = None) -> None:
    payload = blob_store.read_blob(job.id) or {}
    if insights is None:
        insights = payload.get("insights") if isinstance(payload.get("insights"), dict) else payload
    job.status = JobStatus.completed
    job.blob_url = str(blob_store.blob_path(job.id))
    job.error = None
    if job.document_id:
        doc = await session.get(Document, job.document_id)
        if doc:
            doc.analysis_status = AnalysisStatus.completed
            doc.insights = insights
    await session.commit()
    await set_job_status_cache(job.id, JobStatus.completed.value, {"blob_url": job.blob_url})


async def heartbeat_loop(job_id: uuid.UUID, stop: asyncio.Event) -> None:
    """Keep the Postgres lease alive while the mock LLM is running."""
    settings = get_settings()
    interval = max(1.0, settings.lease_seconds / 3)
    while not stop.is_set():
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval)
            return
        except asyncio.TimeoutError:
            now = datetime.now(timezone.utc)
            async with SessionLocal() as session:
                await session.execute(
                    update(Job)
                    .where(
                        Job.id == job_id,
                        Job.worker_id == WORKER_ID,
                        Job.status == JobStatus.processing,
                    )
                    .values(lease_expires_at=now + timedelta(seconds=settings.lease_seconds))
                )
                await session.commit()


async def process_job(job_id: uuid.UUID) -> None:
    settings = get_settings()
    async with SessionLocal() as session:
        job = await claim_job(session, job_id)
        if not job:
            return

        # Duplicate worker / retry after success: blob is source of completion.
        if blob_store.blob_exists(job.id):
            await complete_from_blob(session, job)
            print(f"[{WORKER_ID}] already had blob, marked completed {job.id}")
            return

        await set_job_status_cache(job.id, JobStatus.processing.value, {"worker_id": WORKER_ID})
        if job.document_id:
            doc = await session.get(Document, job.document_id)
            if doc:
                doc.analysis_status = AnalysisStatus.processing
                await session.commit()

        stop = asyncio.Event()
        hb = asyncio.create_task(heartbeat_loop(job.id, stop))
        try:
            await asyncio.sleep(settings.mock_llm_delay_seconds)
            if random.random() < settings.mock_llm_failure_rate:
                raise RuntimeError("mock_llm_transient_error")

            prompt_tokens = random.randint(200, 800)
            completion_tokens = random.randint(100, 400)
            insights = {
                "summary": f"Mock analysis for job {job.id}",
                "topics": ["reliability", "cost", "tenancy"],
                "entities": [{"name": "OmniView", "type": "product"}],
                "confidence": 0.92,
            }
            blob_url = blob_store.write_blob(
                job.id, {"job_id": str(job.id), "insights": insights, "worker_id": WORKER_ID}
            )
            cost = await compute_cost(
                session, job.provider, job.model, prompt_tokens, completion_tokens
            )

            job.status = JobStatus.completed
            job.blob_url = blob_url
            job.error = None
            if job.document_id:
                doc = await session.get(Document, job.document_id)
                if doc:
                    doc.analysis_status = AnalysisStatus.completed
                    doc.insights = insights

            if not await _has_success_usage(session, job.id):
                session.add(
                    LlmUsageEvent(
                        org_id=job.org_id,
                        workspace_id=job.workspace_id,
                        job_id=job.id,
                        provider=job.provider,
                        model=job.model,
                        tokens_prompt=prompt_tokens,
                        tokens_completion=completion_tokens,
                        cost_usd=cost,
                        status=UsageStatus.success,
                        workflow_name=job.workflow_name,
                    )
                )
            await session.commit()
            await set_job_status_cache(job.id, JobStatus.completed.value, {"blob_url": blob_url})
            print(f"[{WORKER_ID}] completed {job.id}")

        except Exception as exc:  # noqa: BLE001
            await session.rollback()
            job = await session.get(Job, job_id)
            if not job:
                return
            blob_already = blob_store.blob_exists(job.id)

            # Blob already written ⇒ this is a false failure. Do not mark failed.
            if blob_already:
                await complete_from_blob(session, job)
                print(f"[{WORKER_ID}] recovered false failure via blob {job.id}")
                return

            job.retry_count += 1
            job.error = str(exc)
            if job.retry_count >= settings.max_job_retries:
                job.status = JobStatus.dlq
                if job.document_id:
                    doc = await session.get(Document, job.document_id)
                    if doc:
                        doc.analysis_status = AnalysisStatus.failed
                session.add(
                    LlmUsageEvent(
                        org_id=job.org_id,
                        workspace_id=job.workspace_id,
                        job_id=job.id,
                        provider=job.provider,
                        model=job.model,
                        tokens_prompt=0,
                        tokens_completion=0,
                        cost_usd=Decimal("0"),
                        status=UsageStatus.failed,
                        workflow_name=job.workflow_name,
                        error_code="max_retries",
                    )
                )
                await session.commit()
                await move_to_dlq(job.id, str(exc))
                await set_job_status_cache(job.id, JobStatus.dlq.value, {"error": str(exc)})
                print(f"[{WORKER_ID}] DLQ {job.id}: {exc}")
            else:
                # Re-queue in a claimable state (queued), not failed.
                job.status = JobStatus.queued
                job.worker_id = None
                job.lease_expires_at = None
                if job.document_id:
                    doc = await session.get(Document, job.document_id)
                    if doc:
                        doc.analysis_status = AnalysisStatus.queued
                session.add(
                    LlmUsageEvent(
                        org_id=job.org_id,
                        workspace_id=job.workspace_id,
                        job_id=job.id,
                        provider=job.provider,
                        model=job.model,
                        tokens_prompt=0,
                        tokens_completion=0,
                        cost_usd=Decimal("0"),
                        status=UsageStatus.failed,
                        workflow_name=job.workflow_name,
                        error_code="transient",
                    )
                )
                await session.commit()
                await set_job_status_cache(job.id, JobStatus.queued.value, {"error": str(exc)})
                await get_redis().lpush(settings.job_queue_key, str(job.id))
                print(f"[{WORKER_ID}] failed {job.id} retry={job.retry_count}: {exc}")
        finally:
            stop.set()
            hb.cancel()
            try:
                await hb
            except asyncio.CancelledError:
                pass


async def run_forever() -> None:
    settings = get_settings()
    r = get_redis()
    print(f"[{WORKER_ID}] listening on {settings.job_queue_key}")
    while True:
        try:
            item = await r.brpop(settings.job_queue_key, timeout=5)
        except Exception as exc:  # noqa: BLE001
            print(f"[{WORKER_ID}] queue poll error: {exc}")
            await asyncio.sleep(1)
            continue
        if not item:
            continue
        _, job_id_str = item
        try:
            job_id = uuid.UUID(job_id_str)
        except ValueError:
            print(f"[{WORKER_ID}] invalid job id: {job_id_str}")
            continue
        await process_job(job_id)


if __name__ == "__main__":
    if os.getenv("MOCK_LLM_FAILURE_RATE"):
        get_settings.cache_clear()
    asyncio.run(run_forever())
