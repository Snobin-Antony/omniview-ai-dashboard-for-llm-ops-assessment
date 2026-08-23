import { useQuery } from "@tanstack/react-query";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api";
import { useApp } from "../state/AppContext";

export default function UsagePage({ workspaceId }: { workspaceId: string }) {
  const { userId } = useApp();
  const q = useQuery({
    queryKey: ["usage", "workspace", workspaceId],
    queryFn: () => api.usage(userId, workspaceId),
  });

  if (q.isLoading) {
    return <Skeleton />;
  }
  if (q.isError) {
    return (
      <ErrorBox
        message={(q.error as Error).message}
        onRetry={() => q.refetch()}
      />
    );
  }

  const data = q.data!;
  const chartData = Object.values(
    data.by_provider_model.reduce<
      Record<string, { name: string; cost: number; requests: number; failed: number }>
    >((acc, row) => {
      const key = `${row.provider}/${row.model}`;
      if (!acc[key]) acc[key] = { name: key, cost: 0, requests: 0, failed: 0 };
      acc[key].cost += Number(row.total_cost_usd);
      acc[key].requests += row.total_requests;
      acc[key].failed += row.failed_request_count;
      return acc;
    }, {})
  );

  return (
    <div className="space-y-6">
      <header>
        <h2 className="text-2xl font-semibold">AI Provider Usage</h2>
        <p className="text-sm text-slate-600">
          Workspace analytics from materialized rollups (Postgres DECIMAL costs).
        </p>
      </header>

      <div className="grid gap-4 sm:grid-cols-3">
        <Stat label="Period spend (USD)" value={Number(data.daily_spend).toFixed(6)} />
        <Stat label="Total requests" value={String(data.total_requests)} />
        <Stat label="Failed requests" value={String(data.failed_request_count)} />
      </div>

      <section className="rounded-xl border border-line bg-panel p-4 shadow-sm">
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
          Provider / model breakdown
        </h3>
        {chartData.length === 0 ? (
          <Empty message="No usage events yet. Run a document analysis job to emit cost events." />
        ) : (
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend />
                <Bar dataKey="cost" name="Cost USD" fill="#0d9488" />
                <Bar dataKey="failed" name="Failed" fill="#f43f5e" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </section>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-line bg-panel p-4 shadow-sm">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 font-mono text-xl font-semibold">{value}</p>
    </div>
  );
}

function Skeleton() {
  return <div className="h-40 animate-pulse rounded-xl bg-slate-200/70" />;
}

function Empty({ message }: { message: string }) {
  return <p className="text-sm text-slate-600">{message}</p>;
}

function ErrorBox({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="rounded border border-red-200 bg-red-50 p-4 text-sm">
      <p className="text-red-800">{message}</p>
      <button
        className="mt-2 rounded bg-ink px-3 py-1 text-white"
        onClick={onRetry}
        type="button"
      >
        Retry
      </button>
    </div>
  );
}
