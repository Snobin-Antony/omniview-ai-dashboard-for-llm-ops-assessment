from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models import AnalysisStatus, JobStatus, Provider, Role, UsageStatus


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserOut(ORMModel):
    id: UUID
    email: str
    display_name: str


class MembershipOut(ORMModel):
    org_id: UUID
    workspace_id: Optional[UUID]
    role: Role


class MeOut(BaseModel):
    user: UserOut
    memberships: list[MembershipOut]
    orgs: list["OrgOut"]
    workspaces: list["WorkspaceOut"]


class OrgOut(ORMModel):
    id: UUID
    name: str


class WorkspaceOut(ORMModel):
    id: UUID
    org_id: UUID
    name: str


class JobCreate(BaseModel):
    workspace_id: UUID
    document_id: Optional[UUID] = None
    provider: Provider = Provider.openai
    model: str = "gpt-4o-mini"
    workflow_name: str = "document_analysis"


class JobOut(ORMModel):
    id: UUID
    org_id: UUID
    workspace_id: UUID
    document_id: Optional[UUID]
    status: JobStatus
    worker_id: Optional[str]
    lease_expires_at: Optional[datetime]
    blob_url: Optional[str]
    error: Optional[str]
    retry_count: int
    provider: Provider
    model: str
    workflow_name: str
    created_at: datetime
    updated_at: datetime
    redis_status: Optional[str] = None
    reconciled: bool = False


class DocumentOut(ORMModel):
    id: UUID
    org_id: UUID
    workspace_id: UUID
    owner_id: UUID
    title: str
    analysis_status: AnalysisStatus
    insights: Optional[dict[str, Any]]
    created_at: datetime
    owner_name: Optional[str] = None


class DocumentListOut(BaseModel):
    items: list[DocumentOut]
    next_cursor: Optional[str] = None


class UsageBreakdownRow(BaseModel):
    day: date
    provider: str
    model: str
    total_cost_usd: Decimal
    total_requests: int
    failed_request_count: int
    tokens_prompt: int
    tokens_completion: int


class UsageSummaryOut(BaseModel):
    workspace_id: UUID
    from_date: date
    to_date: date
    daily_spend: Decimal
    failed_request_count: int
    total_requests: int
    by_provider_model: list[UsageBreakdownRow]


class HealthOut(BaseModel):
    status: str
    postgres: bool
    redis: bool


MeOut.model_rebuild()
