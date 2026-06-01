"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { PodcastGenerator } from "@/components/toolkits/podcast-generator";
import { PodcastEpisodeList } from "@/components/toolkits/podcast-episode-list";

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
  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

  useEffect(() => {
    fetch(`${apiBase}/podcast/episodes`)
      .then((r) => r.json())
      .then((data: Episode[]) => setEpisodes(data))
      .catch(() => {});
  }, [apiBase]);

  const handleNewEpisode = useCallback((ep: Episode) => {
    setEpisodes((prev) => [ep, ...prev]);
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <Link
          href="/toolkits"
          className="text-xs text-cream/30 hover:text-cream/60 transition-colors mb-2 inline-flex items-center gap-1"
        >
          ← Toolkits
        </Link>
        <div className="flex items-center gap-3">
          <span className="text-3xl">🎙</span>
          <div>
            <span className="text-xs font-semibold uppercase tracking-[0.28em] text-ember">
              Toolkits
            </span>
            <h1 className="font-display text-2xl text-cream leading-tight">
              YouTube Podcast
            </h1>
          </div>
        </div>
        <p className="text-cream/40 text-sm mt-1 ml-12">
          Paste a YouTube link — get a digested Chinese podcast episode.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[2fr_3fr] gap-0 rounded-2xl border border-white/10 overflow-hidden min-h-[600px]">
        <div className="border-b lg:border-b-0 lg:border-r border-white/10 bg-white/[0.02] p-6">
          <PodcastGenerator onEpisodeReady={handleNewEpisode} />
        </div>
        <div className="p-6">
          <div className="mb-4">
            <span className="text-xs font-semibold uppercase tracking-[0.28em] text-cream/40">
              My Episodes
            </span>
            <span className="ml-2 text-[10px] text-cream/20">
              {episodes.length > 0 ? `${episodes.length} episode${episodes.length === 1 ? "" : "s"}` : ""}
            </span>
          </div>
          <PodcastEpisodeList episodes={episodes} />
        </div>
      </div>
    </div>
  );
}
