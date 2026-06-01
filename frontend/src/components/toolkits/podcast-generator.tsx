"use client";

import { useEffect, useRef, useState } from "react";
import { API_BASE } from "@/lib/api";

interface Episode {
  id: number;
  video_title: string | null;
  digest_length_mins: number;
  format: string;
  duration_secs: number | null;
  created_at: string;
}

interface PodcastGeneratorProps {
  onEpisodeReady: (episode: Episode) => void;
}

type ProgressStatus =
  | "idle"
  | "extracting"
  | "digesting"
  | "translating"
  | "tts"
  | "stitching"
  | "done"
  | "error";

const STATUS_LABELS: Record<ProgressStatus, string> = {
  idle: "",
  extracting: "Fetching transcript...",
  digesting: "Digesting with Claude...",
  translating: "Translating to Chinese...",
  tts: "Generating audio...",
  stitching: "Stitching dialogue...",
  done: "Done!",
  error: "Generation failed",
};

const VALID_STATUSES = new Set<string>(Object.keys(STATUS_LABELS));

const YOUTUBE_RE =
  /(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})/;

export function PodcastGenerator({ onEpisodeReady }: PodcastGeneratorProps) {
  const [url, setUrl] = useState("");
  const [digestMins, setDigestMins] = useState<5 | 10>(5);
  const [format, setFormat] = useState<"single" | "dialogue">("single");
  const [voiceId, setVoiceId] = useState("21m00Tcm4TlvDq8ikWAM");
  const [status, setStatus] = useState<ProgressStatus>("idle");
  const [errorMsg, setErrorMsg] = useState("");

  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);

  const isGenerating = status !== "idle" && status !== "done" && status !== "error";
  const urlValid = YOUTUBE_RE.test(url);

  async function handleGenerate() {
    if (!urlValid || isGenerating) return;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setStatus("extracting");
    setErrorMsg("");

    try {
      const response = await fetch(`${API_BASE}/podcast/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          youtube_url: url,
          digest_length_mins: digestMins,
          format,
          ...(format === "single" ? { voice_id: voiceId } : {}),
        }),
        signal: controller.signal,
      });

      if (!response.ok || !response.body) {
        throw new Error("Failed to start generation");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done || controller.signal.aborted) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data:")) continue;
          try {
            const payload = JSON.parse(line.slice(5).trim());
            if (payload.status && VALID_STATUSES.has(payload.status)) {
              setStatus(payload.status as ProgressStatus);
            }
            if (payload.status === "done" && payload.episode) {
              onEpisodeReady(payload.episode);
              setUrl("");
            }
            if (payload.status === "error") {
              setErrorMsg(payload.message ?? "Unknown error");
            }
          } catch {
            // ignore malformed SSE lines
          }
        }
      }
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") return;
      setStatus("error");
      setErrorMsg("Connection failed — is the backend running?");
    }
  }

  return (
    <div className="space-y-5">
      <span className="text-xs font-semibold uppercase tracking-[0.28em] text-ink/40">
        Generate New Episode
      </span>

      {/* URL input */}
      <div className="space-y-1.5">
        <label className="text-xs font-medium text-ink/60">YouTube URL</label>
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://youtube.com/watch?v=..."
          disabled={isGenerating}
          className={`w-full rounded-xl border px-3 py-2.5 text-sm bg-white text-ink placeholder:text-ink/30 outline-none transition-colors ${
            url && !urlValid
              ? "border-red-400 focus:border-red-500"
              : "border-ink/15 focus:border-ember"
          } disabled:opacity-40`}
        />
        {url && !urlValid && (
          <p className="text-[11px] text-red-500">Please enter a valid YouTube URL</p>
        )}
      </div>

      {/* Digest length */}
      <div className="space-y-1.5">
        <label className="text-xs font-medium text-ink/60">Digest length</label>
        <div className="flex gap-2">
          {([5, 10] as const).map((mins) => (
            <button
              key={mins}
              onClick={() => setDigestMins(mins)}
              disabled={isGenerating}
              className={`flex-1 rounded-xl py-2 text-sm font-medium transition-colors disabled:opacity-40 ${
                digestMins === mins
                  ? "bg-ember/15 text-ember border border-ember/40"
                  : "bg-white text-ink/50 border border-ink/15 hover:border-ink/30"
              }`}
            >
              ~{mins} min
            </button>
          ))}
        </div>
      </div>

      {/* Format */}
      <div className="space-y-1.5">
        <label className="text-xs font-medium text-ink/60">Format</label>
        <div className="flex gap-2">
          {(["single", "dialogue"] as const).map((fmt) => (
            <button
              key={fmt}
              onClick={() => setFormat(fmt)}
              disabled={isGenerating}
              className={`flex-1 rounded-xl py-2 text-sm font-medium transition-colors disabled:opacity-40 ${
                format === fmt
                  ? "bg-ember/15 text-ember border border-ember/40"
                  : "bg-white text-ink/50 border border-ink/15 hover:border-ink/30"
              }`}
            >
              {fmt === "single" ? "单人叙述" : "双人对话"}
            </button>
          ))}
        </div>
        <p className="text-[11px] text-ink/40">
          {format === "dialogue"
            ? "Two hosts (A + B) discuss the content — takes slightly longer"
            : "Single narrator reads the digest"}
        </p>
      </div>

      {/* Voice selector — single only */}
      {format === "single" && (
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-ink/60">Voice</label>
          <select
            value={voiceId}
            onChange={(e) => setVoiceId(e.target.value)}
            disabled={isGenerating}
            className="w-full rounded-xl border border-ink/15 bg-white px-3 py-2.5 text-sm text-ink outline-none transition-colors focus:border-ember disabled:opacity-40"
          >
            <option value="21m00Tcm4TlvDq8ikWAM">Rachel (Female)</option>
            <option value="AZnzlk1XvdvUeBnXmlld">Domi (Female)</option>
          </select>
        </div>
      )}

      {/* Progress / Generate button */}
      {isGenerating ? (
        <div className="rounded-xl border border-ember/20 bg-ember/5 px-4 py-3">
          <div className="flex items-center gap-2">
            <svg className="animate-spin h-4 w-4 text-ember flex-shrink-0" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
            </svg>
            <span className="text-sm text-ember">{STATUS_LABELS[status]}</span>
          </div>
        </div>
      ) : (
        <button
          onClick={handleGenerate}
          disabled={!urlValid}
          className="w-full rounded-xl bg-ember py-3 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-30"
        >
          <span aria-hidden="true">🎙</span>{" "}Generate Podcast
        </button>
      )}

      {/* Success */}
      {status === "done" && (
        <div className="rounded-xl border border-pine/20 bg-mint/30 px-4 py-3 text-sm text-pine font-medium">
          ✓ Episode ready — check the list on the right!
        </div>
      )}

      {/* Error */}
      {status === "error" && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3">
          <p className="text-sm text-red-600">{errorMsg}</p>
          <button
            onClick={() => setStatus("idle")}
            className="text-xs text-red-400 hover:text-red-600 mt-1 underline"
          >
            Try again
          </button>
        </div>
      )}
    </div>
  );
}
