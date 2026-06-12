"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { AudioLines, Sparkles, List } from "lucide-react";
import { ScribeGenerator, type Transcript } from "@/components/toolkits/scribe-generator";
import { ScribeList } from "@/components/toolkits/scribe-list";
import { API_BASE } from "@/lib/api";

export default function ScribePage() {
  const [items, setItems] = useState<Transcript[]>([]);
  const [loadError, setLoadError] = useState(false);
  const [mobileTab, setMobileTab] = useState<"generate" | "library">("library");

  useEffect(() => {
    fetch(`${API_BASE}/scribe/list`)
      .then((r) => r.json())
      .then((data: Transcript[]) => {
        setItems(data);
        if (data.length === 0) setMobileTab("generate");
      })
      .catch(() => setLoadError(true));
  }, []);

  const handleNew = useCallback((t: Transcript) => {
    setItems((prev) => [t, ...prev]);
    setMobileTab("library");
  }, []);

  const handleDelete = useCallback((id: number) => {
    setItems((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <Link href="/toolkits" className="text-xs text-ink/40 hover:text-ember transition-colors mb-2 inline-flex items-center gap-1">
          ← 蒸馏所
        </Link>
        <div className="flex items-center gap-3 mt-1">
          <div className="flex-shrink-0 w-11 h-11 rounded-[14px] bg-gradient-to-br from-indigo-400 via-indigo-600 to-indigo-700 text-white flex items-center justify-center shadow-[0_6px_16px_-6px_rgba(79,70,229,0.6)]">
            <AudioLines className="w-6 h-6" strokeWidth={2} />
          </div>
          <div>
            <span className="text-xs font-semibold uppercase tracking-[0.28em] text-ember">蒸馏所 · Distill</span>
            <h1 className="font-display text-2xl text-ink leading-tight">录 <span className="text-ink/40 text-lg font-medium">Scribe</span></h1>
          </div>
        </div>
        <p className="text-ink/55 text-sm mt-2">把无字幕的 YouTube 视频转写成文字稿（原语言）。</p>
      </div>

      <div className="lg:hidden flex gap-1.5 rounded-2xl bg-ink/5 p-1">
        <button
          onClick={() => setMobileTab("generate")}
          className={`flex-1 flex items-center justify-center gap-1.5 rounded-xl py-2.5 text-sm font-semibold transition-colors ${mobileTab === "generate" ? "bg-white shadow-sm text-indigo-600" : "text-ink/50"}`}
        >
          <Sparkles className="w-4 h-4" strokeWidth={2} /> 转写
        </button>
        <button
          onClick={() => setMobileTab("library")}
          className={`flex-1 flex items-center justify-center gap-1.5 rounded-xl py-2.5 text-sm font-semibold transition-colors ${mobileTab === "library" ? "bg-white shadow-sm text-indigo-600" : "text-ink/50"}`}
        >
          <List className="w-4 h-4" strokeWidth={2} /> 我的文字稿
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[2fr_3fr] rounded-[28px] border border-ink/10 bg-white/85 shadow-panel overflow-hidden lg:min-h-[600px]">
        <div className={`${mobileTab === "generate" ? "block" : "hidden"} lg:block relative overflow-hidden border-b lg:border-b-0 lg:border-r border-ink/10 bg-sand/20 p-5 lg:p-6`}>
          <AudioLines className="pointer-events-none absolute -right-6 -bottom-7 w-36 h-36 text-indigo-600 opacity-[0.05]" strokeWidth={1.5} />
          <div className="relative z-10">
            <ScribeGenerator onReady={handleNew} />
          </div>
        </div>

        <div className={`${mobileTab === "library" ? "block" : "hidden"} lg:block p-5 lg:p-6`}>
          <div className="flex items-baseline gap-2 mb-4 lg:mb-5">
            <span className="text-xs font-semibold uppercase tracking-[0.28em] text-ink/40">My Transcripts</span>
            {items.length > 0 && (
              <span className="text-[10px] text-ink/30">{items.length} {items.length === 1 ? "transcript" : "transcripts"}</span>
            )}
          </div>
          <ScribeList items={items} loadError={loadError} onDelete={handleDelete} />
        </div>
      </div>
    </div>
  );
}
