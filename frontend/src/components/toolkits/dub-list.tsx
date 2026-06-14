"use client";

import { useState } from "react";
import { Languages } from "lucide-react";
import { API_BASE } from "@/lib/api";
import type { Dub } from "./dub-generator";

interface Props {
  items: Dub[];
  loadError?: boolean;
  onDelete: (id: number) => void;
}

function fmtDur(secs: number | null): string {
  if (secs == null) return "—";
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  return `${m}m ${s.toString().padStart(2, "0")}s`;
}

function fmtDate(iso: string): string {
  const d = new Date(iso);
  const diff = new Date().getTime() - d.getTime();
  if (diff < 86400000) return "Today";
  if (diff < 172800000) return "Yesterday";
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function DubCard({ d, onDelete }: { d: Dub; onDelete: (id: number) => void }) {
  const [open, setOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  async function handleDelete(e: React.MouseEvent) {
    e.stopPropagation();
    if (!confirm("删除这个配音视频？文件会从服务器移除。")) return;
    setDeleting(true);
    try {
      const res = await fetch(`${API_BASE}/dub/${d.id}`, { method: "DELETE" });
      if (!res.ok) throw new Error();
      onDelete(d.id);
    } catch {
      setDeleting(false);
    }
  }

  return (
    <div className="rounded-2xl border border-ink/10 bg-white p-4 hover:border-[#dd9a85] hover:shadow-sm transition-all">
      <div className="flex items-start gap-3 cursor-pointer" onClick={() => setOpen((o) => !o)}>
        <div className="flex-shrink-0 w-9 h-9 rounded-xl bg-[#fbeee9] text-[#c2502f] flex items-center justify-center">
          <Languages className="w-[18px] h-[18px]" strokeWidth={2} />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-ink truncate">{d.title}</p>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-[11px] px-2 py-0.5 rounded-full font-medium bg-[#fbeee9] text-[#c2502f]">中文配音</span>
            <span className="text-[11px] text-ink/20">·</span>
            <span className="text-[11px] text-ink/40">{fmtDur(d.duration_secs)}</span>
            <span className="text-[11px] text-ink/20">·</span>
            <span className="text-[11px] text-ink/40">{fmtDate(d.created_at)}</span>
          </div>
        </div>
        <button
          onClick={handleDelete}
          disabled={deleting}
          aria-label="删除"
          className="flex items-center justify-center w-10 h-10 rounded-full text-ink/40 hover:text-red-400 hover:bg-red-50 transition-colors text-xl leading-none disabled:opacity-40"
        >
          {deleting ? "…" : "×"}
        </button>
      </div>

      {open && (
        <div className="mt-4 pt-4 border-t border-ink/10 space-y-3">
          <video controls className="w-full rounded-xl bg-black" src={`${API_BASE}/dub/${d.id}/video`} />
          <a
            href={`${API_BASE}/dub/${d.id}/video`}
            download={`dub-${d.id}.mp4`}
            onClick={(e) => e.stopPropagation()}
            className="inline-block text-xs font-medium px-3 py-1.5 rounded-lg border border-ink/15 text-ink/60 hover:border-[#d2694a] hover:text-[#b9472f] transition-colors"
          >
            下载 mp4
          </a>
        </div>
      )}
    </div>
  );
}

export function DubList({ items, loadError, onDelete }: Props) {
  if (loadError) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3">
        <p className="text-sm text-red-600">加载失败 — 后端在运行吗？</p>
      </div>
    );
  }
  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <div className="text-5xl mb-4 opacity-20">🎬</div>
        <p className="text-sm font-medium text-ink/40">还没有配音视频</p>
        <p className="text-xs text-ink/30 mt-1">用左边的生成器配第一个视频</p>
      </div>
    );
  }
  return (
    <div className="space-y-3">
      {items.map((d) => (
        <DubCard key={d.id} d={d} onDelete={onDelete} />
      ))}
    </div>
  );
}
