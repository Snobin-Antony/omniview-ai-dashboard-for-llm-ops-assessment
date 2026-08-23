"""Shared fixtures — bind async engine to the pytest-asyncio session loop."""
from __future__ import annotations

import pytest_asyncio

from app.db import SessionLocal, engine
from app.redis_client import reset_redis_client
from app.seed import create_schema, seed


@pytest_asyncio.fixture(scope="session", loop_scope="session", autouse=True)
async def prepare_db():
    # Engine may have been created at import on another loop
    await engine.dispose()
    reset_redis_client()
    await create_schema()
    async with SessionLocal() as session:
        await seed(session)
    yield
    await engine.dispose()
    reset_redis_client()
