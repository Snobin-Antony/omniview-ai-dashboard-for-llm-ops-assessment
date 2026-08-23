from __future__ import annotations

import json
import uuid
from typing import Any, Optional

import redis.asyncio as redis

from app.config import get_settings

_client: Optional[redis.Redis] = None


def get_redis() -> redis.Redis:
    global _client
    if _client is None:
        # socket_timeout=None so BRPOP can block without client TimeoutError
        _client = redis.from_url(
            get_settings().redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=None,
        )
    return _client


def reset_redis_client() -> None:
    """Drop cached client (e.g. after event-loop change in tests)."""
    global _client
    _client = None


def job_status_key(job_id: uuid.UUID) -> str:
    return f"omniview:job:{job_id}:status"


async def set_job_status_cache(job_id: uuid.UUID, status: str, extra: dict[str, Any] | None = None) -> None:
    payload = {"status": status, **(extra or {})}
    await get_redis().set(job_status_key(job_id), json.dumps(payload), ex=3600)


async def get_job_status_cache(job_id: uuid.UUID) -> dict[str, Any] | None:
    raw = await get_redis().get(job_status_key(job_id))
    if not raw:
        return None
    return json.loads(raw)


async def enqueue_job(job_id: uuid.UUID) -> None:
    settings = get_settings()
    await get_redis().lpush(settings.job_queue_key, str(job_id))


async def move_to_dlq(job_id: uuid.UUID, reason: str) -> None:
    settings = get_settings()
    await get_redis().lpush(settings.job_dlq_key, json.dumps({"job_id": str(job_id), "reason": reason}))


async def ping_redis() -> bool:
    try:
        return (await get_redis().ping()) is True
    except Exception:
        return False
