"use client";

import { useEffect, useRef, useState } from "react";
import { API_BASE } from "@/lib/api";

export interface Transcript {
  id: number;
  youtube_url: string;
  title: string;
  transcript: string;
  char_count: number;
  created_at: string;
}

interface Props {
  onReady: (t: Transcript) => void;
}

type Status = "idle" | "downloading" | "transcribing" | "done" | "error";

const STATUS_LABELS: Record<Status, string> = {
  idle: "",
  downloading: "下载音频中...",
  transcribing: "Whisper 转写中...",
  done: "Done!",
  error: "Failed",
};

const VALID_STATUSES = new Set<string>(Object.keys(STATUS_LABELS));
const YOUTUBE_RE = /(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})/;

export function ScribeGenerator({ onReady }: Props) {
  const [url, setUrl] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [errorMsg, setErrorMsg] = useState("");
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => () => abortRef.current?.abort(), []);

  const isBusy = status === "downloading" || status === "transcribing";
  const valid = YOUTUBE_RE.test(url);

  async function handleGenerate() {
    if (!valid || isBusy) return;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setStatus("downloading");
    setErrorMsg("");

    try {
      const response = await fetch(`${API_BASE}/scribe/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ youtube_url: url }),
        signal: controller.signal,
      });
      if (!response.ok || !response.body) throw new Error("Failed to start");

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
            if (payload.status && VALID_STATUSES.has(payload.status)) setStatus(payload.status as Status);
            if (payload.status === "done" && payload.item) {
              onReady(payload.item as Transcript);
              setUrl("");
            }
            if (payload.status === "error") setErrorMsg(payload.message ?? "Unknown error");
          } catch {
            // ignore malformed SSE line
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
        Transcribe 转写
      </span>

      <div className="space-y-1.5">
        <label className="text-xs font-medium text-ink/60">YouTube URL</label>
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://youtube.com/watch?v=..."
          disabled={isBusy}
          className={`w-full rounded-xl border px-3 py-2.5 text-sm bg-white text-ink placeholder:text-ink/30 outline-none transition-colors ${
            url && !valid ? "border-red-400 focus:border-red-500" : "border-ink/15 focus:border-[#a87a3e]"
          } disabled:opacity-40`}
        />
        {url && !valid && <p className="text-[11px] text-red-500">请输入有效的 YouTube 链接</p>}
        <p className="text-[11px] text-ink/40">把无字幕的视频转写成文字稿（原语言）。长视频耗时较久。</p>
      </div>

      {isBusy ? (
        <div className="rounded-xl border border-[#e3d2b0] bg-[#f7f0e6] px-4 py-3 flex items-center gap-2">
          <svg className="animate-spin h-4 w-4 text-[#a87a3e] flex-shrink-0" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
          </svg>
          <span className="text-sm text-[#9a6a34]">{STATUS_LABELS[status]}</span>
        </div>
      ) : (
        <button
          onClick={handleGenerate}
          disabled={!valid}
          className="w-full rounded-xl bg-[#9a6a34] py-3 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-30"
        >
          <span aria-hidden="true">🎧</span> 生成文字稿 Transcribe
        </button>
      )}

      {status === "done" && (
        <div className="rounded-xl border border-[#e3d2b0] bg-[#f7f0e6] px-4 py-3 text-sm text-[#9a6a34] font-medium">
          ✓ 文字稿已生成 — 见右侧列表！
        </div>
      )}
      {status === "error" && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3">
          <p className="text-sm text-red-600">{errorMsg}</p>
          <button onClick={() => setStatus("idle")} className="text-xs text-red-400 hover:text-red-600 mt-1 underline">
            Try again
          </button>
        </div>
      )}
    </div>
  );
}
