"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Flame, Sparkles, List } from "lucide-react";
import { PodcastGenerator } from "@/components/toolkits/podcast-generator";
import { PodcastEpisodeList } from "@/components/toolkits/podcast-episode-list";
import { API_BASE } from "@/lib/api";

interface Episode {
  id: number;
  video_title: string | null;
  digest_length_mins: number;
  format: string;
  duration_secs: number | null;
  created_at: string;
}

export default function PodcastPage() {
  const [episodes, setEpisodes] = useState<Episode[]>([]);
  const [loadError, setLoadError] = useState(false);
  const [mobileTab, setMobileTab] = useState<"generate" | "library">("library");

  useEffect(() => {
    fetch(`${API_BASE}/podcast/episodes`)
      .then((r) => r.json())
      .then((data: Episode[]) => {
        setEpisodes(data);
        if (data.length === 0) setMobileTab("generate");
      })
      .catch(() => setLoadError(true));
  }, []);

  const handleNewEpisode = useCallback((ep: Episode) => {
    setEpisodes((prev) => [ep, ...prev]);
    setMobileTab("library");
  }, []);

  const handleDeleteEpisode = useCallback((id: number) => {
    setEpisodes((prev) => prev.filter((e) => e.id !== id));
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link href="/toolkits" className="text-xs text-ink/40 hover:text-[#d9531e] transition-colors mb-2 inline-flex items-center gap-1">
          ← 蒸馏所
        </Link>
        <div className="flex items-center gap-3 mt-1">
          <div className="flex-shrink-0 w-11 h-11 rounded-[14px] bg-gradient-to-br from-[#f0894a] via-[#d9531e] to-[#b8410f] text-white flex items-center justify-center shadow-[0_6px_16px_-6px_rgba(217,83,30,0.6)]">
            <Flame className="w-6 h-6" strokeWidth={2} />
          </div>
          <div>
            <span className="text-xs font-semibold uppercase tracking-[0.28em] text-[#d9531e]">蒸馏所 · Distill</span>
            <h1 className="font-display text-2xl text-ink leading-tight">炼 <span className="text-ink/40 text-lg font-medium">Forge</span></h1>
          </div>
        </div>
        <p className="text-ink/55 text-sm mt-2">把 YouTube 视频炼成中文播客 —— 单人讲述或双人对话。</p>
      </div>

      {/* Mobile tabs */}
      <div className="lg:hidden flex gap-1.5 rounded-2xl bg-ink/5 p-1">
        <button
          onClick={() => setMobileTab("generate")}
          className={`flex-1 flex items-center justify-center gap-1.5 rounded-xl py-2.5 text-sm font-semibold transition-colors ${mobileTab === "generate" ? "bg-white shadow-sm text-[#d9531e]" : "text-ink/50"}`}
        >
          <Sparkles className="w-4 h-4" strokeWidth={2} /> 生成
        </button>
        <button
          onClick={() => setMobileTab("library")}
          className={`flex-1 flex items-center justify-center gap-1.5 rounded-xl py-2.5 text-sm font-semibold transition-colors ${mobileTab === "library" ? "bg-white shadow-sm text-[#d9531e]" : "text-ink/50"}`}
        >
          <List className="w-4 h-4" strokeWidth={2} /> 我的播客
        </button>
      </div>

      {/* Split panel */}
      <div className="grid grid-cols-1 lg:grid-cols-[2fr_3fr] rounded-[28px] border border-ink/10 bg-white/85 shadow-panel overflow-hidden lg:min-h-[600px]">
        {/* Generator */}
        <div className={`${mobileTab === "generate" ? "block" : "hidden"} lg:block relative overflow-hidden border-b lg:border-b-0 lg:border-r border-ink/10 bg-sand/20 p-5 lg:p-6`}>
          <Flame className="pointer-events-none absolute -right-6 -bottom-7 w-36 h-36 text-[#d9531e] opacity-[0.05]" strokeWidth={1.5} />
          <div className="relative z-10">
            <PodcastGenerator onEpisodeReady={handleNewEpisode} />
          </div>
        </div>

        {/* Library */}
        <div className={`${mobileTab === "library" ? "block" : "hidden"} lg:block p-5 lg:p-6`}>
          <div className="flex items-baseline gap-2 mb-4 lg:mb-5">
            <span className="text-xs font-semibold uppercase tracking-[0.28em] text-ink/40">My Episodes</span>
            {episodes.length > 0 && (
              <span className="text-[10px] text-ink/30">{episodes.length} episode{episodes.length === 1 ? "" : "s"}</span>
            )}
          </div>
          <PodcastEpisodeList episodes={episodes} loadError={loadError} onDelete={handleDeleteEpisode} />
        </div>
      </div>
    </div>
  );
}
