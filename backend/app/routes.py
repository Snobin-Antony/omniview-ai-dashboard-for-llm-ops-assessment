from __future__ import annotations

from datetime import date, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    CurrentUser,
    get_current_user,
    verify_org_owner,
    verify_workspace_access,
    verify_workspace_admin,
)
from app.db import get_db
from app.models import Job, Org, User, Workspace
from app.redis_client import get_job_status_cache, ping_redis
from app.schemas import (
    DocumentListOut,
    DocumentOut,
    HealthOut,
    JobCreate,
    JobOut,
    MeOut,
    MembershipOut,
    OrgOut,
    UsageSummaryOut,
    UserOut,
    WorkspaceOut,
)
from app.services import documents as doc_svc
from app.services import jobs as job_svc
from app.services import usage as usage_svc

router = APIRouter()


@router.get("/health", response_model=HealthOut)
async def health(db: AsyncSession = Depends(get_db)) -> HealthOut:
    pg_ok = False
    try:
        await db.execute(select(1))
        pg_ok = True
    except Exception:
        pg_ok = False
    redis_ok = await ping_redis()
    status = "ok" if pg_ok and redis_ok else "degraded"
    return HealthOut(status=status, postgres=pg_ok, redis=redis_ok)


@router.get("/me", response_model=MeOut)
async def me(
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MeOut:
    org_ids = current.org_ids()
    orgs = []
    if org_ids:
        result = await db.execute(select(Org).where(Org.id.in_(org_ids)))
        orgs = list(result.scalars().all())

    # workspaces: all in owned orgs + explicit memberships
    ws_ids = {m.workspace_id for m in current.memberships if m.workspace_id}
    owned_orgs = {m.org_id for m in current.memberships if m.role.value == "org_owner" and m.workspace_id is None}
    q = select(Workspace)
    if owned_orgs:
        q = q.where((Workspace.org_id.in_(owned_orgs)) | (Workspace.id.in_(ws_ids or {UUID(int=0)})))
    elif ws_ids:
        q = q.where(Workspace.id.in_(ws_ids))
    else:
        workspaces: list[Workspace] = []
        return MeOut(
            user=UserOut.model_validate(current.user),
            memberships=[MembershipOut.model_validate(m) for m in current.memberships],
            orgs=[OrgOut.model_validate(o) for o in orgs],
            workspaces=[],
        )
    result = await db.execute(q)
    workspaces = list(result.scalars().all())
    return MeOut(
        user=UserOut.model_validate(current.user),
        memberships=[MembershipOut.model_validate(m) for m in current.memberships],
        orgs=[OrgOut.model_validate(o) for o in orgs],
        workspaces=[WorkspaceOut.model_validate(w) for w in workspaces],
    )


def _job_out(job, redis_status: str | None = None, reconciled: bool = False) -> JobOut:
    data = JobOut.model_validate(job)
    data.redis_status = redis_status
    data.reconciled = reconciled
    return data


@router.post("/workspaces/{workspace_id}/jobs", response_model=JobOut)
async def create_job(
    workspace_id: UUID,
    body: JobCreate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(verify_workspace_access),
) -> JobOut:
    if body.workspace_id != workspace_id:
        raise HTTPException(400, "workspace_id mismatch")
    org_id = await job_svc.workspace_org_id(db, workspace_id)
    if not org_id:
        raise HTTPException(404, "Workspace not found")
    job = await job_svc.create_job(db, body, org_id)
    return _job_out(job)


@router.get("/workspaces/{workspace_id}/jobs", response_model=list[JobOut])
async def list_jobs(
    workspace_id: UUID,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(verify_workspace_access),
) -> list[JobOut]:
    jobs = await job_svc.list_jobs(db, workspace_id)
    return [_job_out(j) for j in jobs]


@router.get("/workspaces/{workspace_id}/jobs/{job_id}", response_model=JobOut)
async def get_job(
    workspace_id: UUID,
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(verify_workspace_access),
) -> JobOut:
    before = await db.get(Job, job_id)
    prev_status = before.status if before else None
    job = await job_svc.get_job_reconciled(db, job_id, workspace_id)
    if not job:
        raise HTTPException(404, "Job not found")
    cache = await get_job_status_cache(job.id)
    redis_status = cache.get("status") if cache else None
    reconciled = bool(prev_status and prev_status.value != job.status.value)
    return _job_out(job, redis_status=redis_status, reconciled=reconciled)


@router.post("/workspaces/{workspace_id}/jobs/{job_id}/retry", response_model=JobOut)
async def retry_job(
    workspace_id: UUID,
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(verify_workspace_access),
) -> JobOut:
    job = await job_svc.retry_job(db, job_id, workspace_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return _job_out(job)


@router.get("/workspaces/{workspace_id}/analytics/usage", response_model=UsageSummaryOut)
async def workspace_usage(
    workspace_id: UUID,
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(verify_workspace_admin),
) -> UsageSummaryOut:
    today = date.today()
    to_date = to_date or today
    from_date = from_date or (to_date - timedelta(days=30))
    await usage_svc.refresh_usage_rollups(db)
    return await usage_svc.get_workspace_usage(db, workspace_id, from_date, to_date)


@router.get("/orgs/{org_id}/analytics/usage", response_model=dict)
async def org_usage(
    org_id: UUID,
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    workspace_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(verify_org_owner),
) -> dict:
    """Org owner view — MVP returns per-workspace summaries."""
    today = date.today()
    to_date = to_date or today
    from_date = from_date or (to_date - timedelta(days=30))
    await usage_svc.refresh_usage_rollups(db)
    q = select(Workspace).where(Workspace.org_id == org_id)
    if workspace_id:
        q = q.where(Workspace.id == workspace_id)
    result = await db.execute(q)
    workspaces = list(result.scalars().all())
    summaries = []
    for ws in workspaces:
        s = await usage_svc.get_workspace_usage(db, ws.id, from_date, to_date)
        summaries.append({"workspace": WorkspaceOut.model_validate(ws), "usage": s})
    return {"org_id": str(org_id), "from": str(from_date), "to": str(to_date), "workspaces": summaries}


@router.get("/workspaces/{workspace_id}/documents", response_model=DocumentListOut)
async def list_documents(
    workspace_id: UUID,
    status: str | None = None,
    owner_id: UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    cursor: str | None = None,
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(verify_workspace_access),
) -> DocumentListOut:
    docs, next_cursor = await doc_svc.list_documents(
        db,
        workspace_id,
        status=status,
        owner_id=owner_id,
        date_from=date_from,
        date_to=date_to,
        cursor=cursor,
        limit=limit,
    )
    owner_ids = {d.owner_id for d in docs}
    owners = {}
    if owner_ids:
        r = await db.execute(select(User).where(User.id.in_(owner_ids)))
        owners = {u.id: u.display_name for u in r.scalars().all()}
    items = []
    for d in docs:
        out = DocumentOut.model_validate(d)
        out.owner_name = owners.get(d.owner_id)
        items.append(out)
    return DocumentListOut(items=items, next_cursor=next_cursor)


@router.get("/workspaces/{workspace_id}/documents/{document_id}", response_model=DocumentOut)
async def get_document(
    workspace_id: UUID,
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(verify_workspace_access),
) -> DocumentOut:
    doc = await doc_svc.get_document(db, workspace_id, document_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    owner = await db.get(User, doc.owner_id)
    out = DocumentOut.model_validate(doc)
    out.owner_name = owner.display_name if owner else None
    return out


@router.post("/workspaces/{workspace_id}/documents/{document_id}/analyze", response_model=JobOut)
async def analyze_document(
    workspace_id: UUID,
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(verify_workspace_access),
) -> JobOut:
    doc = await doc_svc.get_document(db, workspace_id, document_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    org_id = doc.org_id
    job = await job_svc.create_job(
        db,
        JobCreate(workspace_id=workspace_id, document_id=document_id),
        org_id,
    )
    return _job_out(job)
