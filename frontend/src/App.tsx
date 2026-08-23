import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { Link, Navigate, Route, Routes } from "react-router-dom";
import { api } from "./api";
import { useApp } from "./state/AppContext";
import DocumentsPage from "./pages/DocumentsPage";
import JobsPage from "./pages/JobsPage";
import UsagePage from "./pages/UsagePage";

export default function App() {
  const { userId, setUserId, workspaceId, setWorkspaceId, users } = useApp();
  const me = useQuery({
    queryKey: ["me", userId],
    queryFn: () => api.me(userId),
  });

  const workspaces = me.data?.workspaces ?? [];
  const activeWs =
    workspaceId && workspaces.some((w) => w.id === workspaceId)
      ? workspaceId
      : workspaces[0]?.id ?? null;

  useEffect(() => {
    if (activeWs && activeWs !== workspaceId) {
      setWorkspaceId(activeWs);
    }
  }, [activeWs, workspaceId, setWorkspaceId]);

  return (
    <div className="min-h-screen">
      <header className="border-b border-line bg-panel/90 backdrop-blur sticky top-0 z-20">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-4 px-4 py-3">
          <div>
            <p className="font-mono text-xs uppercase tracking-widest text-accent">OmniView</p>
            <h1 className="text-lg font-semibold">LLM Ops Demo</h1>
          </div>
          <nav className="ml-auto flex flex-wrap gap-3 text-sm font-medium">
            <Link className="hover:text-accent" to="/usage">
              Usage
            </Link>
            <Link className="hover:text-accent" to="/documents">
              Documents
            </Link>
            <Link className="hover:text-accent" to="/jobs">
              Jobs
            </Link>
          </nav>
          <label className="text-xs text-slate-600">
            User
            <select
              className="ml-2 rounded border border-line bg-white px-2 py-1 text-sm"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
            >
              {users.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.label}
                </option>
              ))}
            </select>
          </label>
          <label className="text-xs text-slate-600">
            Workspace
            <select
              className="ml-2 rounded border border-line bg-white px-2 py-1 text-sm"
              value={activeWs ?? ""}
              onChange={(e) => setWorkspaceId(e.target.value)}
              disabled={!workspaces.length}
            >
              {workspaces.map((w) => (
                <option key={w.id} value={w.id}>
                  {w.name}
                </option>
              ))}
            </select>
          </label>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-6">
        {me.isError && (
          <div className="mb-4 rounded border border-red-200 bg-red-50 p-3 text-sm text-red-800">
            Auth/API error: {(me.error as Error).message}. Is the backend running and seeded?
          </div>
        )}
        {!activeWs && !me.isLoading && (
          <p className="text-sm text-slate-600">No workspace available for this user.</p>
        )}
        {activeWs && (
          <Routes>
            <Route path="/" element={<Navigate to="/usage" replace />} />
            <Route path="/usage" element={<UsagePage workspaceId={activeWs} />} />
            <Route path="/documents" element={<DocumentsPage workspaceId={activeWs} />} />
            <Route path="/jobs" element={<JobsPage workspaceId={activeWs} />} />
          </Routes>
        )}
      </main>
    </div>
  );
}
