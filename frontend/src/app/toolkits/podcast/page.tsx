"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Flame } from "lucide-react";
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
  // Mobile only: generator is collapsed by default so the episode list (what you
  // mostly do on mobile — listen) is primary. Desktop always shows the form.
  const [genOpen, setGenOpen] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE}/podcast/episodes`)
      .then((r) => r.json())
      .then((data: Episode[]) => {
        setEpisodes(data);
        // First run with no episodes: open the generator so there's a clear CTA.
        if (data.length === 0) setGenOpen(true);
      })
      .catch(() => setLoadError(true));
  }, []);

  const handleNewEpisode = useCallback((ep: Episode) => {
    setEpisodes((prev) => [ep, ...prev]);
  }, []);

  const handleDeleteEpisode = useCallback((id: number) => {
    setEpisodes((prev) => prev.filter((e) => e.id !== id));
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link
          href="/toolkits"
          className="text-xs text-ink/40 hover:text-ember transition-colors mb-2 inline-flex items-center gap-1"
        >
          ← 蒸馏所
        </Link>
        <div className="flex items-center gap-3 mt-1">
          <div className="flex-shrink-0 w-11 h-11 rounded-[14px] bg-ember/12 text-ember flex items-center justify-center">
            <Flame className="w-6 h-6" strokeWidth={2} />
          </div>
          <div>
            <span className="text-xs font-semibold uppercase tracking-[0.28em] text-ember">
              蒸馏所 · Distill
            </span>
            <h1 className="font-display text-2xl text-ink leading-tight">
              炼 <span className="text-ink/40 text-lg font-medium">Forge</span>
            </h1>
          </div>
        </div>
        <p className="text-ink/55 text-sm mt-2">
          把 YouTube 视频炼成中文播客 —— 单人讲述或双人对话。
        </p>
      </div>

      {/* Split panel */}
      <div className="grid grid-cols-1 lg:grid-cols-[2fr_3fr] rounded-[28px] border border-ink/10 bg-white/85 shadow-panel overflow-hidden lg:min-h-[600px]">
        {/* Generator — collapsible on mobile, always open on desktop */}
        <div className="border-b lg:border-b-0 lg:border-r border-ink/10 bg-sand/20">
          {/* Mobile-only accordion trigger */}
          <button
            type="button"
            onClick={() => setGenOpen((o) => !o)}
            aria-expanded={genOpen}
            className="lg:hidden w-full flex items-center justify-between gap-2 px-5 py-4 text-left active:bg-sand/40 transition-colors"
          >
            <span className="flex items-center gap-2 text-sm font-semibold text-ink">
              <span aria-hidden="true">🎙</span> 生成新一期 · New Episode
            </span>
            <svg
              className={`h-4 w-4 flex-shrink-0 text-ink/40 transition-transform ${genOpen ? "rotate-180" : ""}`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          {/* Form: collapsible on mobile, always visible on desktop */}
          <div className={`${genOpen ? "block" : "hidden"} lg:block px-5 pb-5 lg:p-6`}>
            <PodcastGenerator onEpisodeReady={handleNewEpisode} />
          </div>
        </div>

        {/* Episode library — primary content on mobile */}
        <div className="p-5 lg:p-6">
          <div className="flex items-baseline gap-2 mb-4 lg:mb-5">
            <span className="text-xs font-semibold uppercase tracking-[0.28em] text-ink/40">
              My Episodes
            </span>
            {episodes.length > 0 && (
              <span className="text-[10px] text-ink/30">
                {episodes.length} episode{episodes.length === 1 ? "" : "s"}
              </span>
            )}
          </div>
          <PodcastEpisodeList episodes={episodes} loadError={loadError} onDelete={handleDeleteEpisode} />
        </div>
      </div>
    </div>
  );
}
