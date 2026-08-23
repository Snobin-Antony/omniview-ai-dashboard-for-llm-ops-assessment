from __future__ import annotations

import base64
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document


def encode_cursor(created_at: datetime, doc_id: UUID) -> str:
    raw = f"{created_at.isoformat()}|{doc_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    raw = base64.urlsafe_b64decode(cursor.encode()).decode()
    ts, doc_id = raw.split("|", 1)
    return datetime.fromisoformat(ts), UUID(doc_id)


async def list_documents(
    db: AsyncSession,
    workspace_id: UUID,
    *,
    status: Optional[str] = None,
    owner_id: Optional[UUID] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    cursor: Optional[str] = None,
    limit: int = 50,
) -> tuple[list[Document], Optional[str]]:
    filters = [Document.workspace_id == workspace_id]
    if status:
        filters.append(Document.analysis_status == status)
    if owner_id:
        filters.append(Document.owner_id == owner_id)
    if date_from:
        filters.append(Document.created_at >= date_from)
    if date_to:
        filters.append(Document.created_at <= date_to)
    if cursor:
        c_ts, c_id = decode_cursor(cursor)
        filters.append(
            (Document.created_at < c_ts)
            | and_(Document.created_at == c_ts, Document.id < c_id)
        )

    result = await db.execute(
        select(Document)
        .where(*filters)
        .order_by(Document.created_at.desc(), Document.id.desc())
        .limit(limit + 1)
    )
    docs = list(result.scalars().all())
    next_cursor = None
    if len(docs) > limit:
        last = docs[limit - 1]
        docs = docs[:limit]
        next_cursor = encode_cursor(last.created_at, last.id)
    return docs, next_cursor


async def get_document(db: AsyncSession, workspace_id: UUID, document_id: UUID) -> Document | None:
    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.workspace_id == workspace_id)
    )
    return result.scalar_one_or_none()
