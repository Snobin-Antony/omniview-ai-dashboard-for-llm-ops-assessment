"""Create schema, materialized view, and seed demo data."""
from __future__ import annotations

import asyncio
import uuid
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import Base, SessionLocal, engine
from app.models import (
    AnalysisStatus,
    Document,
    Membership,
    Org,
    PricingRate,
    Provider,
    Role,
    User,
    Workspace,
)

# Fixed UUIDs for demo reproducibility
ORG_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
WS_A_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb1")
WS_B_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbb2")
OWNER_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-ccccccccccc1")
ADMIN_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-ccccccccccc2")

MV_SQL = """
CREATE MATERIALIZED VIEW IF NOT EXISTS daily_usage_rollup AS
SELECT
  date_trunc('day', timestamp)::date AS day,
  workspace_id,
  provider::text AS provider,
  model,
  COALESCE(SUM(cost_usd), 0) AS total_cost_usd,
  COUNT(*)::int AS total_requests,
  COUNT(*) FILTER (WHERE status = 'failed')::int AS failed_request_count,
  COALESCE(SUM(tokens_prompt), 0)::int AS tokens_prompt,
  COALESCE(SUM(tokens_completion), 0)::int AS tokens_completion
FROM llm_usage_events
GROUP BY 1, 2, 3, 4
WITH NO DATA;
"""

MV_INDEX = """
CREATE UNIQUE INDEX IF NOT EXISTS ix_daily_usage_rollup_pk
ON daily_usage_rollup (day, workspace_id, provider, model);
"""


async def create_schema() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text(MV_SQL))
        await conn.execute(text(MV_INDEX))


async def seed(session: AsyncSession) -> None:
    existing = await session.get(Org, ORG_ID)
    if existing:
        print("Seed already applied.")
        return

    org = Org(id=ORG_ID, name="Acme AI")
    ws_a = Workspace(id=WS_A_ID, org_id=ORG_ID, name="Workspace Alpha")
    ws_b = Workspace(id=WS_B_ID, org_id=ORG_ID, name="Workspace Beta")
    owner = User(id=OWNER_ID, email="owner@acme.test", display_name="Org Owner")
    admin = User(id=ADMIN_ID, email="admin@acme.test", display_name="Workspace Admin")
    session.add_all([org, ws_a, ws_b, owner, admin])
    await session.flush()

    session.add_all(
        [
            Membership(user_id=OWNER_ID, org_id=ORG_ID, workspace_id=None, role=Role.org_owner),
            Membership(
                user_id=ADMIN_ID, org_id=ORG_ID, workspace_id=WS_A_ID, role=Role.workspace_admin
            ),
        ]
    )

    rates = [
        PricingRate(
            provider=Provider.openai,
            model="gpt-4o-mini",
            prompt_per_1k=Decimal("0.000150"),
            completion_per_1k=Decimal("0.000600"),
        ),
        PricingRate(
            provider=Provider.vertex_gemini,
            model="gemini-1.5-flash",
            prompt_per_1k=Decimal("0.000075"),
            completion_per_1k=Decimal("0.000300"),
        ),
        PricingRate(
            provider=Provider.vertex_anthropic,
            model="claude-3-haiku",
            prompt_per_1k=Decimal("0.000250"),
            completion_per_1k=Decimal("0.001250"),
        ),
    ]
    session.add_all(rates)

    docs = []
    for i in range(1, 81):
        ws = WS_A_ID if i % 2 else WS_B_ID
        owner_u = OWNER_ID if i % 3 else ADMIN_ID
        # Admin only owns docs in WS A for realism; clamp for WS B
        if ws == WS_B_ID:
            owner_u = OWNER_ID
        status = AnalysisStatus.pending
        if i % 7 == 0:
            status = AnalysisStatus.completed
        elif i % 11 == 0:
            status = AnalysisStatus.failed
        insights = None
        if status == AnalysisStatus.completed:
            insights = {
                "summary": f"Insights for document {i}",
                "topics": ["ops", "llm", "cost"],
                "sentiment": "neutral",
            }
        docs.append(
            Document(
                org_id=ORG_ID,
                workspace_id=ws,
                owner_id=owner_u,
                title=f"Document {i:03d}",
                analysis_status=status,
                insights=insights,
            )
        )
    session.add_all(docs)
    await session.commit()
    print("Seed complete.")
    print(f"  Org owner user id:      {OWNER_ID}")
    print(f"  Workspace admin user id: {ADMIN_ID}")
    print(f"  Workspace Alpha:         {WS_A_ID}")
    print(f"  Workspace Beta:          {WS_B_ID}")


async def main() -> None:
    await create_schema()
    async with SessionLocal() as session:
        await seed(session)


if __name__ == "__main__":
    asyncio.run(main())
