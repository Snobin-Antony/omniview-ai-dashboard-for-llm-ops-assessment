from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import UsageBreakdownRow, UsageSummaryOut

REFRESH_MV = "REFRESH MATERIALIZED VIEW daily_usage_rollup"


async def refresh_usage_rollups(db: AsyncSession) -> None:
    await db.execute(text(REFRESH_MV))
    await db.commit()


async def get_workspace_usage(
    db: AsyncSession,
    workspace_id: UUID,
    from_date: date,
    to_date: date,
) -> UsageSummaryOut:
    # Prefer MV; fall back to raw events if empty (e.g. before first refresh)
    rows = await db.execute(
        text(
            """
            SELECT day, provider::text, model, total_cost_usd, total_requests,
                   failed_request_count, tokens_prompt, tokens_completion
            FROM daily_usage_rollup
            WHERE workspace_id = :workspace_id
              AND day >= :from_date AND day <= :to_date
            ORDER BY day, provider, model
            """
        ),
        {"workspace_id": workspace_id, "from_date": from_date, "to_date": to_date},
    )
    data = rows.mappings().all()
    if not data:
        rows = await db.execute(
            text(
                """
                SELECT date_trunc('day', timestamp)::date AS day,
                       provider::text AS provider,
                       model,
                       COALESCE(SUM(cost_usd), 0) AS total_cost_usd,
                       COUNT(*)::int AS total_requests,
                       COUNT(*) FILTER (WHERE status = 'failed')::int AS failed_request_count,
                       COALESCE(SUM(tokens_prompt), 0)::int AS tokens_prompt,
                       COALESCE(SUM(tokens_completion), 0)::int AS tokens_completion
                FROM llm_usage_events
                WHERE workspace_id = :workspace_id
                  AND timestamp::date >= :from_date AND timestamp::date <= :to_date
                GROUP BY 1, 2, 3
                ORDER BY 1, 2, 3
                """
            ),
            {"workspace_id": workspace_id, "from_date": from_date, "to_date": to_date},
        )
        data = rows.mappings().all()

    breakdown = [
        UsageBreakdownRow(
            day=r["day"],
            provider=r["provider"],
            model=r["model"],
            total_cost_usd=Decimal(str(r["total_cost_usd"])),
            total_requests=int(r["total_requests"]),
            failed_request_count=int(r["failed_request_count"]),
            tokens_prompt=int(r["tokens_prompt"]),
            tokens_completion=int(r["tokens_completion"]),
        )
        for r in data
    ]
    daily_spend = sum((b.total_cost_usd for b in breakdown), Decimal("0"))
    failed = sum(b.failed_request_count for b in breakdown)
    total = sum(b.total_requests for b in breakdown)
    return UsageSummaryOut(
        workspace_id=workspace_id,
        from_date=from_date,
        to_date=to_date,
        daily_spend=daily_spend,
        failed_request_count=failed,
        total_requests=total,
        by_provider_model=breakdown,
    )
