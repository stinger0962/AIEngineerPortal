"use client";

import { useState } from "react";
import { Layers } from "lucide-react";
import { API_BASE } from "@/lib/api";
import { SummaryView, type Summary } from "./summary-view";

interface SummaryListProps {
  summaries: Summary[];
  loadError?: boolean;
  onDelete: (id: number) => void;
}

const SOURCE_LABEL: Record<string, string> = {
  text: "文本",
  web: "网页",
  youtube: "YouTube",
};

function formatDate(iso: string): string {
  const d = new Date(iso);
  const now = new Date();
  const diff = now.getTime() - d.getTime();
  if (diff < 86400000) return "Today";
  if (diff < 172800000) return "Yesterday";
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function SummaryCard({ s, onDelete }: { s: Summary; onDelete: (id: number) => void }) {
  const [open, setOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  async function handleDelete(e: React.MouseEvent) {
    e.stopPropagation();
    if (!confirm("Delete this summary?")) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      const res = await fetch(`${API_BASE}/summary/${s.id}`, { method: "DELETE" });
      if (!res.ok) throw new Error(`Server error ${res.status}`);
      onDelete(s.id);
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : "Delete failed");
      setDeleting(false);
    }
  }

  return (
    <div className="rounded-2xl border border-ink/10 bg-white p-4 hover:border-teal/30 hover:shadow-sm transition-all">
      <div className="flex items-start gap-3 cursor-pointer" onClick={() => setOpen((o) => !o)}>
        <div className="flex-shrink-0 w-9 h-9 rounded-xl bg-teal/10 text-teal flex items-center justify-center"><Layers className="w-[18px] h-[18px]" strokeWidth={2} /></div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-ink truncate">{s.title}</p>
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            <span className="text-[11px] px-2 py-0.5 rounded-full font-medium bg-ink/8 text-ink/50">
              {SOURCE_LABEL[s.source_type] ?? s.source_type}
            </span>
            <span className="text-[11px] text-ink/20">·</span>
            <span className="text-[11px] text-ink/40">{formatDate(s.created_at)}</span>
          </div>
        </div>
        <button
          onClick={handleDelete}
          disabled={deleting}
          aria-label="Delete summary"
          title="Delete summary"
          className="flex items-center justify-center w-10 h-10 rounded-full text-ink/40 hover:text-red-400 hover:bg-red-50 active:bg-red-100 transition-colors text-xl leading-none disabled:opacity-40"
        >
          {deleting ? "…" : "×"}
        </button>
      </div>

      {!open && <p className="text-xs text-ink/50 mt-2 line-clamp-2">{s.tldr}</p>}
      {open && (
        <div className="mt-4 pt-4 border-t border-ink/10">
          <SummaryView summary={s} />
        </div>
      )}
      {deleteError && <p className="mt-2 text-[11px] text-red-400">{deleteError}</p>}
    </div>
  );
}

export function SummaryList({ summaries, loadError, onDelete }: SummaryListProps) {
  if (loadError) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3">
        <p className="text-sm text-red-600">Failed to load summaries — is the backend running?</p>
      </div>
    );
  }

  if (summaries.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <div className="text-5xl mb-4 opacity-20">📝</div>
        <p className="text-sm font-medium text-ink/40">No summaries yet</p>
        <p className="text-xs text-ink/30 mt-1">用生成器创建第一篇摘要</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {summaries.map((s) => (
        <SummaryCard key={s.id} s={s} onDelete={onDelete} />
      ))}
    </div>
  );
}
