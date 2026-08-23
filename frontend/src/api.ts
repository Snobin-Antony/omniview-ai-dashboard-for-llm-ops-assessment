import type { Document, DocumentList, Job, Me, UsageSummary } from "./types";

const API = "/api/v1";

async function request<T>(
  path: string,
  userId: string,
  init?: RequestInit
): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-User-Id": userId,
      ...(init?.headers || {}),
    },
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  me: (userId: string) => request<Me>("/me", userId),
  health: () => fetch(`${API}/health`).then((r) => r.json()),
  listJobs: (userId: string, workspaceId: string) =>
    request<Job[]>(`/workspaces/${workspaceId}/jobs`, userId),
  getJob: (userId: string, workspaceId: string, jobId: string) =>
    request<Job>(`/workspaces/${workspaceId}/jobs/${jobId}`, userId),
  createJob: (
    userId: string,
    workspaceId: string,
    body: { workspace_id: string; document_id?: string }
  ) =>
    request<Job>(`/workspaces/${workspaceId}/jobs`, userId, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  retryJob: (userId: string, workspaceId: string, jobId: string) =>
    request<Job>(`/workspaces/${workspaceId}/jobs/${jobId}/retry`, userId, {
      method: "POST",
    }),
  usage: (userId: string, workspaceId: string) =>
    request<UsageSummary>(`/workspaces/${workspaceId}/analytics/usage`, userId),
  listDocuments: (
    userId: string,
    workspaceId: string,
    params: Record<string, string | undefined>
  ) => {
    const q = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v) q.set(k, v);
    });
    const qs = q.toString();
    return request<DocumentList>(
      `/workspaces/${workspaceId}/documents${qs ? `?${qs}` : ""}`,
      userId
    );
  },
  getDocument: (userId: string, workspaceId: string, documentId: string) =>
    request<Document>(`/workspaces/${workspaceId}/documents/${documentId}`, userId),
  analyzeDocument: (userId: string, workspaceId: string, documentId: string) =>
    request<Job>(
      `/workspaces/${workspaceId}/documents/${documentId}/analyze`,
      userId,
      { method: "POST" }
    ),
};
