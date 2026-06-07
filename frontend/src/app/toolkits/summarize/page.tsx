"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { SummaryGenerator } from "@/components/toolkits/summary-generator";
import { SummaryList } from "@/components/toolkits/summary-list";
import type { Summary } from "@/components/toolkits/summary-view";
import { API_BASE } from "@/lib/api";

export default function SummarizePage() {
  const [summaries, setSummaries] = useState<Summary[]>([]);
  const [loadError, setLoadError] = useState(false);
  const [genOpen, setGenOpen] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE}/summary/list`)
      .then((r) => r.json())
      .then((data: Summary[]) => {
        setSummaries(data);
        if (data.length === 0) setGenOpen(true);
      })
      .catch(() => setLoadError(true));
  }, []);

  const handleNew = useCallback((s: Summary) => {
    setSummaries((prev) => [s, ...prev]);
  }, []);

  const handleDelete = useCallback((id: number) => {
    setSummaries((prev) => prev.filter((s) => s.id !== id));
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <Link
          href="/toolkits"
          className="text-xs text-ink/40 hover:text-ember transition-colors mb-2 inline-flex items-center gap-1"
        >
          ← Toolkits
        </Link>
        <div className="flex items-center gap-3 mt-1">
          <span className="text-3xl">📝</span>
          <div>
            <span className="text-xs font-semibold uppercase tracking-[0.28em] text-ember">
              Toolkits
            </span>
            <h1 className="font-display text-2xl text-ink leading-tight">内容摘要 Summarize</h1>
          </div>
        </div>
        <p className="text-ink/50 text-sm mt-1 ml-12">
          粘贴文本、网页或 YouTube 链接 — 获得结构化中文摘要。
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[2fr_3fr] rounded-[28px] border border-ink/10 bg-white/85 shadow-panel overflow-hidden lg:min-h-[600px]">
        <div className="border-b lg:border-b-0 lg:border-r border-ink/10 bg-sand/20">
          <button
            type="button"
            onClick={() => setGenOpen((o) => !o)}
            aria-expanded={genOpen}
            className="lg:hidden w-full flex items-center justify-between gap-2 px-5 py-4 text-left active:bg-sand/40 transition-colors"
          >
            <span className="flex items-center gap-2 text-sm font-semibold text-ink">
              <span aria-hidden="true">📝</span> 生成新摘要 · New Summary
            </span>
            <svg
              className={`h-4 w-4 flex-shrink-0 text-ink/40 transition-transform ${genOpen ? "rotate-180" : ""}`}
              fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          <div className={`${genOpen ? "block" : "hidden"} lg:block px-5 pb-5 lg:p-6`}>
            <SummaryGenerator onSummaryReady={handleNew} />
          </div>
        </div>

        <div className="p-5 lg:p-6">
          <div className="flex items-baseline gap-2 mb-4 lg:mb-5">
            <span className="text-xs font-semibold uppercase tracking-[0.28em] text-ink/40">
              My Summaries
            </span>
            {summaries.length > 0 && (
              <span className="text-[10px] text-ink/30">
                {summaries.length} {summaries.length === 1 ? "summary" : "summaries"}
              </span>
            )}
          </div>
          <SummaryList summaries={summaries} loadError={loadError} onDelete={handleDelete} />
        </div>
      </div>
    </div>
  );
}
