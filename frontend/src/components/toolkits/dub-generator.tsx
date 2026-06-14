"use client";

import { useEffect, useRef, useState } from "react";
import { API_BASE } from "@/lib/api";

export interface Dub {
  id: number;
  youtube_url: string | null;
  title: string;
  voice_id: string;
  duration_secs: number | null;
  created_at: string;
}

interface Voice {
  voice_id: string;
  name: string;
  gender: "female" | "male";
}

interface Props {
  onReady: (d: Dub) => void;
}

type Status =
  | "idle"
  | "uploading"
  | "downloading"
  | "transcribing"
  | "translating"
  | "voicing"
  | "composing"
  | "done"
  | "error";

const STATUS_LABELS: Record<Status, string> = {
  idle: "",
  uploading: "上传中...",
  downloading: "下载视频中...",
  transcribing: "转写中...",
  translating: "翻译中...",
  voicing: "配音中...",
  composing: "合成视频中...",
  done: "Done!",
  error: "Failed",
};

const VALID_STATUSES = new Set<string>(Object.keys(STATUS_LABELS));
const YOUTUBE_RE = /(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})/;
const MAX_UPLOAD_BYTES = 100 * 1024 * 1024;

function fmtMB(bytes: number): string {
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export function DubGenerator({ onReady }: Props) {
  const [mode, setMode] = useState<"link" | "upload">("link");
  const [url, setUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [voiceId, setVoiceId] = useState("random");
  const [voices, setVoices] = useState<Voice[]>([]);
  const [status, setStatus] = useState<Status>("idle");
  const [errorMsg, setErrorMsg] = useState("");
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => () => abortRef.current?.abort(), []);
  useEffect(() => {
    fetch(`${API_BASE}/podcast/voices`)
      .then((r) => r.json())
      .then((data: Voice[]) => setVoices(data))
      .catch(() => setVoices([]));
  }, []);

  const femaleVoices = voices.filter((v) => v.gender === "female");
  const maleVoices = voices.filter((v) => v.gender === "male");
  const isBusy = status !== "idle" && status !== "done" && status !== "error";
  const urlValid = YOUTUBE_RE.test(url);
  const fileTooBig = file != null && file.size > MAX_UPLOAD_BYTES;
  const valid = mode === "link" ? urlValid : file != null && !fileTooBig;

  function onPickFile(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0] ?? null;
    setFile(f);
    setErrorMsg("");
  }

  async function readSse(response: Response, controller: AbortController) {
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
            onReady(payload.item as Dub);
            setUrl("");
            setFile(null);
          }
          if (payload.status === "error") setErrorMsg(payload.message ?? "Unknown error");
        } catch {
          // ignore malformed SSE line
        }
      }
    }
  }

  async function handleGenerate() {
    if (!valid || isBusy) return;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setErrorMsg("");

    try {
      let response: Response;
      if (mode === "link") {
        setStatus("downloading");
        response = await fetch(`${API_BASE}/dub/generate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ youtube_url: url, voice_id: voiceId }),
          signal: controller.signal,
        });
      } else {
        setStatus("uploading");
        const form = new FormData();
        form.append("file", file as File);
        form.append("voice_id", voiceId);
        // No Content-Type header — the browser sets the multipart boundary.
        response = await fetch(`${API_BASE}/dub/generate-upload`, {
          method: "POST",
          body: form,
          signal: controller.signal,
        });
      }
      await readSse(response, controller);
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") return;
      setStatus("error");
      setErrorMsg("Connection failed — is the backend running?");
    }
  }

  return (
    <div className="space-y-5">
      <span className="text-xs font-semibold uppercase tracking-[0.28em] text-ink/40">配音 Dub</span>

      {/* 链接 / 上传 toggle */}
      <div className="flex gap-1.5 rounded-2xl bg-ink/5 p-1">
        <button
          onClick={() => setMode("link")}
          disabled={isBusy}
          className={`flex-1 rounded-xl py-2 text-sm font-semibold transition-colors disabled:opacity-40 ${
            mode === "link" ? "bg-white shadow-sm text-[#b9472f]" : "text-ink/50"
          }`}
        >
          🔗 链接
        </button>
        <button
          onClick={() => setMode("upload")}
          disabled={isBusy}
          className={`flex-1 rounded-xl py-2 text-sm font-semibold transition-colors disabled:opacity-40 ${
            mode === "upload" ? "bg-white shadow-sm text-[#b9472f]" : "text-ink/50"
          }`}
        >
          📁 上传
        </button>
      </div>

      {mode === "link" ? (
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-ink/60">YouTube URL（外语视频）</label>
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://youtube.com/watch?v=..."
            disabled={isBusy}
            className={`w-full rounded-xl border px-3 py-2.5 text-sm bg-white text-ink placeholder:text-ink/30 outline-none transition-colors ${
              url && !urlValid ? "border-red-400 focus:border-red-500" : "border-ink/15 focus:border-[#c2502f]"
            } disabled:opacity-40`}
          />
          {url && !urlValid && <p className="text-[11px] text-red-500">请输入有效的 YouTube 链接</p>}
          <p className="text-[11px] text-ink/40">≤ 10 分钟。原声会被压低做背景，中文旁白盖在上面。</p>
        </div>
      ) : (
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-ink/60">本地视频（手机/电脑）</label>
          <input
            type="file"
            accept="video/*"
            onChange={onPickFile}
            disabled={isBusy}
            className="block w-full text-sm text-ink/70 file:mr-3 file:rounded-lg file:border-0 file:bg-[#b9472f] file:px-3 file:py-2 file:text-sm file:font-semibold file:text-white hover:file:opacity-90 disabled:opacity-40"
          />
          {file && (
            <p className={`text-[11px] ${fileTooBig ? "text-red-500" : "text-ink/50"}`}>
              {file.name} · {fmtMB(file.size)}
              {fileTooBig && " — 超过 100MB 上限，请换更小的文件"}
            </p>
          )}
          <p className="text-[11px] text-ink/40">≤ 100MB、≤ 10 分钟。原声压低做背景，中文旁白盖在上面。</p>
        </div>
      )}

      <div className="space-y-1.5">
        <label className="text-xs font-medium text-ink/60">旁白嗓音 Voice</label>
        <select
          value={voiceId}
          onChange={(e) => setVoiceId(e.target.value)}
          disabled={isBusy}
          className="w-full rounded-xl border border-ink/15 bg-white px-3 py-2.5 text-sm text-ink outline-none transition-colors focus:border-[#c2502f] disabled:opacity-40"
        >
          <option value="random">🎲 随机 Random</option>
          {femaleVoices.length > 0 && (
            <optgroup label="女声 Female">
              {femaleVoices.map((v) => (
                <option key={v.voice_id} value={v.voice_id}>{v.name}</option>
              ))}
            </optgroup>
          )}
          {maleVoices.length > 0 && (
            <optgroup label="男声 Male">
              {maleVoices.map((v) => (
                <option key={v.voice_id} value={v.voice_id}>{v.name}</option>
              ))}
            </optgroup>
          )}
        </select>
      </div>

      {isBusy ? (
        <div className="rounded-xl border border-[#ecc2b5] bg-[#fbeee9] px-4 py-3 flex items-center gap-2">
          <svg className="animate-spin h-4 w-4 text-[#c2502f] flex-shrink-0" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
          </svg>
          <span className="text-sm text-[#b9472f]">{STATUS_LABELS[status]}</span>
        </div>
      ) : (
        <button
          onClick={handleGenerate}
          disabled={!valid}
          className="w-full rounded-xl bg-[#b9472f] py-3 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-30"
        >
          <span aria-hidden="true">🎬</span> 生成配音视频 Dub
        </button>
      )}

      {status === "done" && (
        <div className="rounded-xl border border-[#ecc2b5] bg-[#fbeee9] px-4 py-3 text-sm text-[#b9472f] font-medium">
          ✓ 配音视频已生成 — 见右侧列表！
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
