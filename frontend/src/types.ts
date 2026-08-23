export type Role = "org_owner" | "workspace_admin" | "member";

export interface User {
  id: string;
  email: string;
  display_name: string;
}

export interface Membership {
  org_id: string;
  workspace_id: string | null;
  role: Role;
}

export interface Org {
  id: string;
  name: string;
}

export interface Workspace {
  id: string;
  org_id: string;
  name: string;
}

export interface Me {
  user: User;
  memberships: Membership[];
  orgs: Org[];
  workspaces: Workspace[];
}

export interface Job {
  id: string;
  org_id: string;
  workspace_id: string;
  document_id: string | null;
  status: string;
  worker_id: string | null;
  lease_expires_at: string | null;
  blob_url: string | null;
  error: string | null;
  retry_count: number;
  provider: string;
  model: string;
  workflow_name: string;
  created_at: string;
  updated_at: string;
  redis_status?: string | null;
  reconciled?: boolean;
}

export interface Document {
  id: string;
  org_id: string;
  workspace_id: string;
  owner_id: string;
  title: string;
  analysis_status: string;
  insights: Record<string, unknown> | null;
  created_at: string;
  owner_name?: string | null;
}

export interface DocumentList {
  items: Document[];
  next_cursor: string | null;
}

export interface UsageSummary {
  workspace_id: string;
  from_date: string;
  to_date: string;
  daily_spend: string;
  failed_request_count: number;
  total_requests: number;
  by_provider_model: Array<{
    day: string;
    provider: string;
    model: string;
    total_cost_usd: string;
    total_requests: number;
    failed_request_count: number;
    tokens_prompt: number;
    tokens_completion: number;
  }>;
}

export const SEED_USERS = [
  {
    id: "cccccccc-cccc-cccc-cccc-ccccccccccc1",
    label: "Org Owner",
  },
  {
    id: "cccccccc-cccc-cccc-cccc-ccccccccccc2",
    label: "Workspace Admin (Alpha)",
  },
] as const;
