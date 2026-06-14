"use client";

import { useState } from "react";
import { API_BASE } from "@/lib/api";

interface Episode {
  id: number;
  video_title: string | null;
  digest_length_mins: number;
  format: string;
  duration_secs: number | null;
  created_at: string;
}

interface PodcastEpisodeListProps {
  episodes: Episode[];
  loadError?: boolean;
  onDelete: (id: number) => void;
}

function formatDuration(secs: number | null): string {
  if (secs == null) return "—";
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  return `${m}m ${s.toString().padStart(2, "0")}s`;
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  const now = new Date();
  const diff = now.getTime() - d.getTime();
  if (diff < 86400000) return "Today";
  if (diff < 172800000) return "Yesterday";
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function EpisodeCard({
  ep,
  onDelete,
}: {
  ep: Episode;
  onDelete: (id: number) => void;
}) {
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  async function handleDelete() {
    if (
      !confirm("Delete this episode? The audio file will be removed from the server.")
    ) {
      return;
    }
    setDeleting(true);
    setDeleteError(null);
    try {
      const res = await fetch(`${API_BASE}/podcast/episodes/${ep.id}`, {
        method: "DELETE",
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body?.detail ?? `Server error ${res.status}`);
      }
      onDelete(ep.id);
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : "Delete failed");
      setDeleting(false);
    }
  }

  return (
    <div className="rounded-2xl border border-ink/10 bg-white p-4 hover:border-[#d9531e]/30 hover:shadow-sm transition-all">
      <div className="flex items-start gap-3">
        {/* Icon */}
        <div className="flex-shrink-0 w-9 h-9 rounded-xl bg-[#d9531e]/10 flex items-center justify-center text-base">
          🎙
        </div>

        {/* Meta */}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-ink truncate">
            {ep.video_title ?? "Untitled video"}
          </p>
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            <span className="text-[11px] text-ink/40">
              {formatDuration(ep.duration_secs)}
            </span>
            <span className="text-[11px] text-ink/20">·</span>
            <span
              className={`text-[11px] px-2 py-0.5 rounded-full font-medium ${
                ep.format === "dialogue"
                  ? "bg-pine/10 text-pine"
                  : "bg-ink/8 text-ink/50"
              }`}
            >
              {ep.format === "dialogue" ? "对话" : "单人"}
            </span>
            <span className="text-[11px] text-ink/20">·</span>
            <span className="text-[11px] text-ink/40">{formatDate(ep.created_at)}</span>
          </div>
        </div>

        {/* Actions — 40px touch targets for mobile */}
        <div className="flex items-center gap-0.5 flex-shrink-0 -mr-1">
          {/* Download */}
          <a
            href={`${API_BASE}/podcast/episodes/${ep.id}/download`}
            download={`podcast-${ep.id}.mp3`}
            aria-label="Download episode MP3"
            className="flex items-center justify-center w-10 h-10 rounded-full text-ink/40 hover:text-[#d9531e] hover:bg-[#d9531e]/10 active:bg-[#d9531e]/15 transition-colors text-lg leading-none"
            title="Download MP3"
          >
            ↓
          </a>

          {/* Delete */}
          <button
            onClick={handleDelete}
            disabled={deleting}
            aria-label="Delete episode"
            title="Delete episode"
            className="flex items-center justify-center w-10 h-10 rounded-full text-ink/40 hover:text-red-400 hover:bg-red-50 active:bg-red-100 transition-colors text-xl leading-none disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {deleting ? "…" : "×"}
          </button>
        </div>
      </div>

      {/* Audio player */}
      <div className="mt-3">
        <audio
          controls
          src={`${API_BASE}/podcast/episodes/${ep.id}/download`}
          className="w-full h-8"
        />
      </div>

      {/* Inline delete error */}
      {deleteError && (
        <p className="mt-2 text-[11px] text-red-400">{deleteError}</p>
      )}
    </div>
  );
}

export function PodcastEpisodeList({ episodes, loadError, onDelete }: PodcastEpisodeListProps) {
  if (loadError) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3">
        <p className="text-sm text-red-600">Failed to load episodes — is the backend running?</p>
      </div>
    );
  }

  if (episodes.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <div className="text-5xl mb-4 opacity-20">🎙</div>
        <p className="text-sm font-medium text-ink/40">No episodes yet</p>
        <p className="text-xs text-ink/30 mt-1">
          Use the generator to create your first episode
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {episodes.map((ep) => (
        <EpisodeCard key={ep.id} ep={ep} onDelete={onDelete} />
      ))}
    </div>
  );
}
