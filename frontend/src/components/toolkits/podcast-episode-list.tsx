"use client";

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
}

function formatDuration(secs: number | null): string {
  if (!secs) return "—";
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

export function PodcastEpisodeList({ episodes }: PodcastEpisodeListProps) {
  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

  if (episodes.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full py-20 text-center">
        <div className="text-5xl mb-4 opacity-30">🎙</div>
        <p className="text-cream/40 text-sm font-medium">No episodes yet</p>
        <p className="text-cream/25 text-xs mt-1">
          Generate your first podcast from the form on the left
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {episodes.map((ep) => (
        <div
          key={ep.id}
          className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/5 p-3 hover:border-white/20 transition-colors"
        >
          <div className="flex-shrink-0 w-9 h-9 rounded-lg bg-ember/20 flex items-center justify-center text-base">
            🎙
          </div>

          <div className="flex-1 min-w-0">
            <p className="text-xs font-semibold text-cream truncate">
              {ep.video_title ?? "Untitled video"}
            </p>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="text-[10px] text-cream/40">
                {formatDuration(ep.duration_secs)}
              </span>
              <span className="text-[10px] text-cream/20">·</span>
              <span
                className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
                  ep.format === "dialogue"
                    ? "bg-blue-500/20 text-blue-300"
                    : "bg-white/10 text-cream/40"
                }`}
              >
                {ep.format === "dialogue" ? "对话" : "单人"}
              </span>
              <span className="text-[10px] text-cream/20">·</span>
              <span className="text-[10px] text-cream/40">{formatDate(ep.created_at)}</span>
            </div>
          </div>

          <div className="flex items-center gap-2 flex-shrink-0">
            <audio
              controls
              src={`${apiBase}/podcast/episodes/${ep.id}/download`}
              className="h-7 w-32 opacity-70 hover:opacity-100 transition-opacity"
            />
            <a
              href={`${apiBase}/podcast/episodes/${ep.id}/download`}
              download={`podcast-${ep.id}.mp3`}
              className="text-cream/40 hover:text-ember transition-colors p-1"
              title="Download MP3"
            >
              ↓
            </a>
          </div>
        </div>
      ))}
    </div>
  );
}
