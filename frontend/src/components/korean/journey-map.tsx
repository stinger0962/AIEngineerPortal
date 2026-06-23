"use client";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { koreanApi } from "@/lib/korean/api";
import type { MapNode } from "@/lib/korean/types";

const KIND_ICON: Record<string, string> = { reading: "🔤", scene: "💬", drill: "✍️", boss: "🎯" };

function NodeChip({ node }: { node: MapNode }) {
  const locked = node.status === "locked";
  const body = (
    <div
      className={`rounded-xl border p-3 transition ${
        locked
          ? "border-white/10 bg-white/5 opacity-50"
          : node.status === "completed"
            ? "border-emerald-400/60 bg-emerald-400/10"
            : "border-violet-400/60 bg-violet-400/10 hover:bg-violet-400/20"
      }`}
    >
      <div className="text-xl">{locked ? "🔒" : KIND_ICON[node.kind]}</div>
      <div className="mt-1 text-sm font-medium">{node.title}</div>
      <div className="text-xs opacity-60">{"★".repeat(node.stars) || "—"}</div>
    </div>
  );
  return locked ? body : <Link href={`/korean/node/${node.slug}`}>{body}</Link>;
}

export function JourneyMap() {
  const qc = useQueryClient();
  const { data: regions, isLoading } = useQuery({ queryKey: ["korean-map"], queryFn: koreanApi.getMap });
  const reset = useMutation({
    mutationFn: koreanApi.resetProgress,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["korean-map"] }),
  });

  if (isLoading) return <div className="p-8 opacity-60">Loading…</div>;

  return (
    <div className="mx-auto max-w-4xl p-6">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">한국어 — Journey</h1>
        <button
          className="rounded-lg border border-white/15 px-3 py-1.5 text-sm opacity-80 hover:bg-white/10"
          onClick={() => {
            if (confirm("Reset all Korean progress? This cannot be undone.")) reset.mutate();
          }}
        >
          Reset progress
        </button>
      </div>
      <div className="space-y-8">
        {regions?.map((r) => (
          <section key={r.slug}>
            <h2 className="mb-3 text-lg font-medium opacity-90">{r.title}</h2>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
              {r.nodes.map((n) => (
                <NodeChip key={n.slug} node={n} />
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
