import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api";
import { useApp } from "../state/AppContext";

export default function JobsPage({ workspaceId }: { workspaceId: string }) {
  const { userId } = useApp();
  const qc = useQueryClient();
  const jobs = useQuery({
    queryKey: ["jobs", workspaceId],
    queryFn: () => api.listJobs(userId, workspaceId),
    refetchInterval: 2000,
  });

  const create = useMutation({
    mutationFn: () =>
      api.createJob(userId, workspaceId, { workspace_id: workspaceId }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["jobs", workspaceId] }),
  });

  const retry = useMutation({
    mutationFn: (jobId: string) => api.retryJob(userId, workspaceId, jobId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["jobs", workspaceId] }),
  });

  const checkAgain = useMutation({
    mutationFn: (jobId: string) => api.getJob(userId, workspaceId, jobId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["jobs", workspaceId] }),
  });

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold">Jobs</h2>
          <p className="text-sm text-slate-600">
            Postgres is source of truth; Redis is UI cache. Polling every 2s.
          </p>
        </div>
        <button
          type="button"
          className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white"
          onClick={() => create.mutate()}
          disabled={create.isPending}
        >
          Enqueue mock job
        </button>
      </header>

      {jobs.isLoading && <div className="h-32 animate-pulse rounded-xl bg-slate-200/70" />}
      {jobs.isError && (
        <p className="text-sm text-red-700">{(jobs.error as Error).message}</p>
      )}
      {jobs.data?.length === 0 && (
        <p className="text-sm text-slate-600">No jobs yet. Enqueue one or analyze a document.</p>
      )}

      <ul className="space-y-2">
        {jobs.data?.map((job) => (
          <li
            key={job.id}
            className="rounded-xl border border-line bg-panel p-4 shadow-sm"
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="font-mono text-xs text-slate-500">{job.id}</p>
                <p className="mt-1 text-sm">
                  Status:{" "}
                  <span className="font-semibold capitalize">{job.status}</span>
                  {job.redis_status && job.redis_status !== job.status && (
                    <span className="ml-2 text-xs text-amber-700">
                      redis={job.redis_status}
                    </span>
                  )}
                  {job.reconciled && (
                    <span className="ml-2 text-xs text-teal-700">reconciled</span>
                  )}
                </p>
                <p className="text-xs text-slate-500">
                  {job.provider}/{job.model} · retries {job.retry_count}
                  {job.worker_id ? ` · ${job.worker_id}` : ""}
                </p>
                {job.error && (
                  <p className="mt-1 text-xs text-red-600">{job.error}</p>
                )}
              </div>
              {(job.status === "failed" || job.status === "dlq") && (
                <div className="flex gap-2">
                  <button
                    type="button"
                    className="rounded border border-line px-3 py-1 text-xs"
                    onClick={() => checkAgain.mutate(job.id)}
                  >
                    Check again
                  </button>
                  <button
                    type="button"
                    className="rounded bg-ink px-3 py-1 text-xs text-white"
                    onClick={() => retry.mutate(job.id)}
                  >
                    Retry
                  </button>
                </div>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
