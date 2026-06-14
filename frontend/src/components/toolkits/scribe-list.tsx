"use client";

import { useState } from "react";
import { AudioLines } from "lucide-react";
import { API_BASE } from "@/lib/api";
import type { Transcript } from "./scribe-generator";

interface Props {
  items: Transcript[];
  loadError?: boolean;
  onDelete: (id: number) => void;
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  const now = new Date();
  const diff = now.getTime() - d.getTime();
  if (diff < 86400000) return "Today";
  if (diff < 172800000) return "Yesterday";
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function TranscriptCard({ t, onDelete }: { t: Transcript; onDelete: (id: number) => void }) {
  const [open, setOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [copied, setCopied] = useState(false);

  async function handleDelete(e: React.MouseEvent) {
    e.stopPropagation();
    if (!confirm("删除这份文字稿？")) return;
    setDeleting(true);
    try {
      const res = await fetch(`${API_BASE}/scribe/${t.id}`, { method: "DELETE" });
      if (!res.ok) throw new Error();
      onDelete(t.id);
    } catch {
      setDeleting(false);
    }
  }

  async function handleCopy(e: React.MouseEvent) {
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(t.transcript);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* ignore */
    }
  }

  return (
    <div className="rounded-2xl border border-ink/10 bg-white p-4 hover:border-[#cba672] hover:shadow-sm transition-all">
      <div className="flex items-start gap-3 cursor-pointer" onClick={() => setOpen((o) => !o)}>
        <div className="flex-shrink-0 w-9 h-9 rounded-xl bg-[#f7f0e6] text-[#a87a3e] flex items-center justify-center">
          <AudioLines className="w-[18px] h-[18px]" strokeWidth={2} />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-ink truncate">{t.title}</p>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-[11px] px-2 py-0.5 rounded-full font-medium bg-[#f7f0e6] text-[#a87a3e]">文字稿</span>
            <span className="text-[11px] text-ink/20">·</span>
            <span className="text-[11px] text-ink/40">{t.char_count} 字</span>
            <span className="text-[11px] text-ink/20">·</span>
            <span className="text-[11px] text-ink/40">{formatDate(t.created_at)}</span>
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
          <div className="max-h-[360px] overflow-y-auto rounded-xl border border-ink/10 bg-ink/[0.02] p-3 text-sm text-ink/80 leading-relaxed whitespace-pre-wrap">
            {t.transcript}
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleCopy}
              className="text-xs font-medium px-3 py-1.5 rounded-lg border border-ink/15 text-ink/60 hover:border-[#b88a52] hover:text-[#9a6a34] transition-colors"
            >
              {copied ? "已复制 ✓" : "复制 Copy"}
            </button>
            <a
              href={`${API_BASE}/scribe/${t.id}/download`}
              download={`scribe-${t.id}.txt`}
              onClick={(e) => e.stopPropagation()}
              className="text-xs font-medium px-3 py-1.5 rounded-lg border border-ink/15 text-ink/60 hover:border-[#b88a52] hover:text-[#9a6a34] transition-colors"
            >
              下载 .txt
            </a>
          </div>
        </div>
      )}
    </div>
  );
}

export function ScribeList({ items, loadError, onDelete }: Props) {
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
        <div className="text-5xl mb-4 opacity-20">🎧</div>
        <p className="text-sm font-medium text-ink/40">还没有文字稿</p>
        <p className="text-xs text-ink/30 mt-1">用左边的生成器转写第一个视频</p>
      </div>
    );
  }
  return (
    <div className="space-y-3">
      {items.map((t) => (
        <TranscriptCard key={t.id} t={t} onDelete={onDelete} />
      ))}
    </div>
  );
}
