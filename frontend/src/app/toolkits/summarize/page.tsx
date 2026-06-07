"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Layers, Sparkles, List } from "lucide-react";
import { SummaryGenerator } from "@/components/toolkits/summary-generator";
import { SummaryList } from "@/components/toolkits/summary-list";
import type { Summary } from "@/components/toolkits/summary-view";
import { API_BASE } from "@/lib/api";

export default function SummarizePage() {
  const [summaries, setSummaries] = useState<Summary[]>([]);
  const [loadError, setLoadError] = useState(false);
  const [mobileTab, setMobileTab] = useState<"generate" | "library">("library");

  useEffect(() => {
    fetch(`${API_BASE}/summary/list`)
      .then((r) => r.json())
      .then((data: Summary[]) => {
        setSummaries(data);
        if (data.length === 0) setMobileTab("generate");
      })
      .catch(() => setLoadError(true));
  }, []);

  const handleNew = useCallback((s: Summary) => {
    setSummaries((prev) => [s, ...prev]);
    setMobileTab("library");
  }, []);

  const handleDelete = useCallback((id: number) => {
    setSummaries((prev) => prev.filter((s) => s.id !== id));
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link href="/toolkits" className="text-xs text-ink/40 hover:text-ember transition-colors mb-2 inline-flex items-center gap-1">
          ← 蒸馏所
        </Link>
        <div className="flex items-center gap-3 mt-1">
          <div className="flex-shrink-0 w-11 h-11 rounded-[14px] bg-gradient-to-br from-[#3fa39d] via-teal to-[#155653] text-white flex items-center justify-center shadow-[0_6px_16px_-6px_rgba(31,111,107,0.6)]">
            <Layers className="w-6 h-6" strokeWidth={2} />
          </div>
          <div>
            <span className="text-xs font-semibold uppercase tracking-[0.28em] text-ember">蒸馏所 · Distill</span>
            <h1 className="font-display text-2xl text-ink leading-tight">织 <span className="text-ink/40 text-lg font-medium">Loom</span></h1>
          </div>
        </div>
        <p className="text-ink/55 text-sm mt-2">把文本、网页、YouTube 或微信文章织成结构化中文摘要。</p>
      </div>

      {/* Mobile tabs */}
      <div className="lg:hidden flex gap-1.5 rounded-2xl bg-ink/5 p-1">
        <button
          onClick={() => setMobileTab("generate")}
          className={`flex-1 flex items-center justify-center gap-1.5 rounded-xl py-2.5 text-sm font-semibold transition-colors ${mobileTab === "generate" ? "bg-white shadow-sm text-teal" : "text-ink/50"}`}
        >
          <Sparkles className="w-4 h-4" strokeWidth={2} /> 生成
        </button>
        <button
          onClick={() => setMobileTab("library")}
          className={`flex-1 flex items-center justify-center gap-1.5 rounded-xl py-2.5 text-sm font-semibold transition-colors ${mobileTab === "library" ? "bg-white shadow-sm text-teal" : "text-ink/50"}`}
        >
          <List className="w-4 h-4" strokeWidth={2} /> 我的摘要
        </button>
      </div>

      {/* Split panel */}
      <div className="grid grid-cols-1 lg:grid-cols-[2fr_3fr] rounded-[28px] border border-ink/10 bg-white/85 shadow-panel overflow-hidden lg:min-h-[600px]">
        {/* Generator */}
        <div className={`${mobileTab === "generate" ? "block" : "hidden"} lg:block relative overflow-hidden border-b lg:border-b-0 lg:border-r border-ink/10 bg-sand/20 p-5 lg:p-6`}>
          <Layers className="pointer-events-none absolute -right-6 -bottom-7 w-36 h-36 text-teal opacity-[0.05]" strokeWidth={1.5} />
          <div className="relative z-10">
            <SummaryGenerator onSummaryReady={handleNew} />
          </div>
        </div>

        {/* Library */}
        <div className={`${mobileTab === "library" ? "block" : "hidden"} lg:block p-5 lg:p-6`}>
          <div className="flex items-baseline gap-2 mb-4 lg:mb-5">
            <span className="text-xs font-semibold uppercase tracking-[0.28em] text-ink/40">My Summaries</span>
            {summaries.length > 0 && (
              <span className="text-[10px] text-ink/30">{summaries.length} {summaries.length === 1 ? "summary" : "summaries"}</span>
            )}
          </div>
          <SummaryList summaries={summaries} loadError={loadError} onDelete={handleDelete} />
        </div>
      </div>
    </div>
  );
}
