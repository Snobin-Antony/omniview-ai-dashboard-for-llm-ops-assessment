from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.models import Membership, Role, User


@dataclass
class CurrentUser:
    user: User
    memberships: list[Membership]

    @property
    def id(self) -> uuid.UUID:
        return self.user.id

    def is_org_owner(self, org_id: uuid.UUID) -> bool:
        return any(
            m.org_id == org_id and m.role == Role.org_owner and m.workspace_id is None
            for m in self.memberships
        )

    def is_workspace_admin(self, workspace_id: uuid.UUID) -> bool:
        for m in self.memberships:
            if m.workspace_id == workspace_id and m.role in (Role.workspace_admin, Role.org_owner):
                return True
            if m.workspace_id is None and m.role == Role.org_owner:
                # org owners can access all workspaces in their org — verified with workspace org later
                return True
        return False

    def org_ids(self) -> set[uuid.UUID]:
        return {m.org_id for m in self.memberships}


async def get_current_user(
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    if not x_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-User-Id header (mock auth)",
        )
    try:
        user_uuid = uuid.UUID(x_user_id)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid X-User-Id") from exc

    result = await db.execute(
        select(User)
        .where(User.id == user_uuid)
        .options(selectinload(User.memberships))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return CurrentUser(user=user, memberships=list(user.memberships))


async def verify_org_owner(
    org_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    if not current.is_org_owner(org_id):
        raise HTTPException(status_code=403, detail="Org owner role required")
    return current


async def verify_workspace_access(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    from app.models import Workspace

    ws = await db.get(Workspace, workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    if current.is_org_owner(ws.org_id):
        return current

    allowed = any(
        m.workspace_id == workspace_id
        and m.role in (Role.workspace_admin, Role.member, Role.org_owner)
        for m in current.memberships
    )
    if not allowed:
        raise HTTPException(status_code=403, detail="No access to this workspace")
    return current


async def verify_workspace_admin(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    from app.models import Workspace

    ws = await db.get(Workspace, workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    if current.is_org_owner(ws.org_id):
        return current

    allowed = any(
        m.workspace_id == workspace_id and m.role == Role.workspace_admin
        for m in current.memberships
    )
    if not allowed:
        raise HTTPException(status_code=403, detail="Workspace admin role required")
    return current
