"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
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

  useEffect(() => {
    fetch(`${API_BASE}/podcast/episodes`)
      .then((r) => r.json())
      .then((data: Episode[]) => setEpisodes(data))
      .catch(() => setLoadError(true));
  }, []);

  const handleNewEpisode = useCallback((ep: Episode) => {
    setEpisodes((prev) => [ep, ...prev]);
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link
          href="/toolkits"
          className="text-xs text-ink/40 hover:text-ember transition-colors mb-2 inline-flex items-center gap-1"
        >
          ← Toolkits
        </Link>
        <div className="flex items-center gap-3 mt-1">
          <span className="text-3xl">🎙</span>
          <div>
            <span className="text-xs font-semibold uppercase tracking-[0.28em] text-ember">
              Toolkits
            </span>
            <h1 className="font-display text-2xl text-ink leading-tight">
              YouTube Podcast
            </h1>
          </div>
        </div>
        <p className="text-ink/50 text-sm mt-1 ml-12">
          Paste a YouTube link — get a digested Chinese podcast episode.
        </p>
      </div>

      {/* Split panel */}
      <div className="grid grid-cols-1 lg:grid-cols-[2fr_3fr] rounded-[28px] border border-ink/10 bg-white/85 shadow-panel overflow-hidden min-h-[600px]">
        {/* Left: generator */}
        <div className="border-b lg:border-b-0 lg:border-r border-ink/10 p-6 bg-sand/20">
          <PodcastGenerator onEpisodeReady={handleNewEpisode} />
        </div>

        {/* Right: episode library */}
        <div className="p-6">
          <div className="flex items-baseline gap-2 mb-5">
            <span className="text-xs font-semibold uppercase tracking-[0.28em] text-ink/40">
              My Episodes
            </span>
            {episodes.length > 0 && (
              <span className="text-[10px] text-ink/30">
                {episodes.length} episode{episodes.length === 1 ? "" : "s"}
              </span>
            )}
          </div>
          <PodcastEpisodeList episodes={episodes} loadError={loadError} />
        </div>
      </div>
    </div>
  );
}
