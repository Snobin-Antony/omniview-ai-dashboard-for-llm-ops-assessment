import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useVirtualizer } from "@tanstack/react-virtual";
import { useMemo, useRef } from "react";
import { useSearchParams } from "react-router-dom";
import { DocumentRepository } from "../storage/DocumentRepository";
import { useApp } from "../state/AppContext";

export default function DocumentsPage({ workspaceId }: { workspaceId: string }) {
  const { userId } = useApp();
  const [params, setParams] = useSearchParams();
  const status = params.get("status") || "";
  const docId = params.get("doc") || "";
  const qc = useQueryClient();
  const parentRef = useRef<HTMLDivElement>(null);

  const list = useInfiniteQuery({
    queryKey: ["workspace", workspaceId, "documents", { status }],
    queryFn: ({ pageParam }) =>
      DocumentRepository.list(userId, workspaceId, {
        status: status || undefined,
        cursor: pageParam as string | undefined,
        limit: "40",
      }),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last) => last.next_cursor ?? undefined,
  });

  const items = useMemo(
    () => list.data?.pages.flatMap((p) => p.items) ?? [],
    [list.data]
  );

  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 56,
    overscan: 8,
  });

  const selected = useQuery({
    queryKey: ["workspace", workspaceId, "document", docId],
    queryFn: () => DocumentRepository.get(userId, workspaceId, docId),
    enabled: Boolean(docId),
  });

  const analyze = useMutation({
    mutationFn: (id: string) => DocumentRepository.analyze(userId, workspaceId, id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["workspace", workspaceId, "documents"] });
      qc.invalidateQueries({ queryKey: ["jobs", workspaceId] });
    },
  });

  function setFilter(nextStatus: string) {
    const p = new URLSearchParams(params);
    if (nextStatus) p.set("status", nextStatus);
    else p.delete("status");
    setParams(p);
  }

  function selectDoc(id: string) {
    const p = new URLSearchParams(params);
    p.set("doc", id);
    setParams(p);
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_340px]">
      <section className="space-y-3">
        <header>
          <h2 className="text-2xl font-semibold">Document Insights</h2>
          <p className="text-sm text-slate-600">
            Virtualized list · filters in URL · DocumentRepository facade (no IndexedDB).
          </p>
        </header>

        <DocumentFilters status={status} onStatus={setFilter} />

        {list.isLoading && (
          <div className="space-y-2">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="h-12 animate-pulse rounded-lg bg-slate-200/70" />
            ))}
          </div>
        )}
        {list.isError && (
          <div className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-800">
            {(list.error as Error).message}
            <button className="ml-2 underline" type="button" onClick={() => list.refetch()}>
              Retry
            </button>
          </div>
        )}
        {!list.isLoading && items.length === 0 && (
          <p className="text-sm text-slate-600">
            {status
              ? "No documents match these filters."
              : "No documents yet in this workspace."}
            {status && (
              <button className="ml-2 text-accent underline" type="button" onClick={() => setFilter("")}>
                Clear filters
              </button>
            )}
          </p>
        )}

        <div
          ref={parentRef}
          className="h-[520px] overflow-auto rounded-xl border border-line bg-panel"
          onScroll={() => {
            const el = parentRef.current;
            if (!el || !list.hasNextPage || list.isFetchingNextPage) return;
            if (el.scrollTop + el.clientHeight >= el.scrollHeight - 80) {
              list.fetchNextPage();
            }
          }}
        >
          <div
            style={{ height: virtualizer.getTotalSize(), position: "relative", width: "100%" }}
          >
            {virtualizer.getVirtualItems().map((row) => {
              const doc = items[row.index];
              return (
                <button
                  key={doc.id}
                  type="button"
                  className={`absolute left-0 top-0 flex w-full items-center justify-between border-b border-line px-4 text-left hover:bg-mist ${
                    docId === doc.id ? "bg-teal-50" : ""
                  }`}
                  style={{ height: row.size, transform: `translateY(${row.start}px)` }}
                  onClick={() => selectDoc(doc.id)}
                >
                  <span>
                    <span className="block text-sm font-medium">{doc.title}</span>
                    <span className="text-xs text-slate-500">
                      {doc.owner_name || doc.owner_id.slice(0, 8)} · {doc.analysis_status}
                    </span>
                  </span>
                  <span className="rounded-full bg-mist px-2 py-0.5 font-mono text-[10px] uppercase">
                    {doc.analysis_status}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
        {list.isFetchingNextPage && (
          <p className="text-xs text-slate-500">Loading more…</p>
        )}
      </section>

      <aside className="rounded-xl border border-line bg-panel p-4 shadow-sm">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          Details
        </h3>
        {!docId && <p className="mt-3 text-sm text-slate-600">Select a document.</p>}
        {docId && selected.isLoading && (
          <div className="mt-3 h-40 animate-pulse rounded bg-slate-200/70" />
        )}
        {docId && selected.isError && (
          <div className="mt-3 text-sm text-red-700">
            {(selected.error as Error).message}
            <button className="ml-2 underline" type="button" onClick={() => selected.refetch()}>
              Retry
            </button>
          </div>
        )}
        {selected.data && (
          <div className="mt-3 space-y-3 text-sm">
            <p className="font-semibold">{selected.data.title}</p>
            <p className="text-xs text-slate-500">Status: {selected.data.analysis_status}</p>
            <button
              type="button"
              className="rounded bg-accent px-3 py-1.5 text-xs font-medium text-white"
              disabled={analyze.isPending}
              onClick={() => analyze.mutate(selected.data.id)}
            >
              Run analysis job
            </button>
            <pre className="max-h-72 overflow-auto rounded bg-mist p-2 font-mono text-[11px]">
              {selected.data.insights
                ? JSON.stringify(selected.data.insights, null, 2)
                : "No insights yet."}
            </pre>
          </div>
        )}
      </aside>
    </div>
  );
}

function DocumentFilters({
  status,
  onStatus,
}: {
  status: string;
  onStatus: (s: string) => void;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {["", "pending", "queued", "processing", "completed", "failed"].map((s) => (
        <button
          key={s || "all"}
          type="button"
          onClick={() => onStatus(s)}
          className={`rounded-full border px-3 py-1 text-xs ${
            status === s
              ? "border-accent bg-teal-50 text-accent"
              : "border-line bg-white text-slate-600"
          }`}
        >
          {s || "all"}
        </button>
      ))}
    </div>
  );
}
