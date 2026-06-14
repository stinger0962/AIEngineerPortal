"use client";

import { useEffect, useRef, useState } from "react";
import { API_BASE } from "@/lib/api";
import type { Summary } from "./summary-view";

interface Props {
  onSummaryReady: (summary: Summary) => void;
}

type Status = "idle" | "fetching" | "summarizing" | "mapping" | "done" | "error";

const STATUS_LABELS: Record<Status, string> = {
  idle: "",
  fetching: "Fetching content...",
  summarizing: "Summarizing with Claude...",
  mapping: "Building mind map...",
  done: "Done!",
  error: "Failed",
};

const VALID_STATUSES = new Set<string>(Object.keys(STATUS_LABELS));
type SourceType = "text" | "web" | "youtube";

export function SummaryGenerator({ onSummaryReady }: Props) {
  const [sourceType, setSourceType] = useState<SourceType>("text");
  const [value, setValue] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [outputType, setOutputType] = useState<"summary" | "mindmap">("summary");
  const [errorMsg, setErrorMsg] = useState("");
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => () => abortRef.current?.abort(), []);

  const isBusy = status === "fetching" || status === "summarizing" || status === "mapping";
  const valid = value.trim().length > 0;

  async function handleGenerate() {
    if (!valid || isBusy) return;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setStatus("fetching");
    setErrorMsg("");

    try {
      const response = await fetch(`${API_BASE}/summary/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source_type: sourceType, value, output_type: outputType }),
        signal: controller.signal,
      });
      if (!response.ok || !response.body) throw new Error("Failed to start");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value: chunk } = await reader.read();
        if (done || controller.signal.aborted) break;
        buffer += decoder.decode(chunk, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";
        for (const line of lines) {
          if (!line.startsWith("data:")) continue;
          try {
            const payload = JSON.parse(line.slice(5).trim());
            if (payload.status && VALID_STATUSES.has(payload.status)) {
              setStatus(payload.status as Status);
            }
            if (payload.status === "done" && payload.summary) {
              onSummaryReady(payload.summary as Summary);
              setValue("");
            }
            if (payload.status === "error") {
              setErrorMsg(payload.message ?? "Unknown error");
            }
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
        Generate Summary
      </span>

      <div className="space-y-1.5">
        <label className="text-xs font-medium text-ink/60">Output 输出</label>
        <div className="flex gap-2">
          {([["summary", "摘要"], ["mindmap", "思维导图"]] as const).map(([val, label]) => (
            <button
              key={val}
              onClick={() => setOutputType(val)}
              disabled={isBusy}
              className={`flex-1 rounded-xl py-2 text-sm font-medium transition-colors disabled:opacity-40 ${
                outputType === val
                  ? "bg-[#c0892e]/15 text-[#c0892e] border border-[#c0892e]/40"
                  : "bg-white text-ink/50 border border-ink/15 hover:border-ink/30"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-1.5">
        <label className="text-xs font-medium text-ink/60">Source</label>
        <div className="flex gap-2">
          {(["text", "web", "youtube"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setSourceType(t)}
              disabled={isBusy}
              className={`flex-1 rounded-xl py-2 text-sm font-medium transition-colors disabled:opacity-40 ${
                sourceType === t
                  ? "bg-[#c0892e]/15 text-[#c0892e] border border-[#c0892e]/40"
                  : "bg-white text-ink/50 border border-ink/15 hover:border-ink/30"
              }`}
            >
              {t === "text" ? "文本" : t === "web" ? "网页" : "YouTube"}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-1.5">
        {sourceType === "text" ? (
          <textarea
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="粘贴要总结的文本..."
            disabled={isBusy}
            rows={8}
            className="w-full rounded-xl border border-ink/15 bg-white px-3 py-2.5 text-sm text-ink placeholder:text-ink/30 outline-none transition-colors focus:border-[#c0892e] disabled:opacity-40 resize-none"
          />
        ) : (
          <input
            type="url"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder={sourceType === "web" ? "https://example.com/article" : "https://youtube.com/watch?v=..."}
            disabled={isBusy}
            className="w-full rounded-xl border border-ink/15 bg-white px-3 py-2.5 text-sm text-ink placeholder:text-ink/30 outline-none transition-colors focus:border-[#c0892e] disabled:opacity-40"
          />
        )}
      </div>

      {isBusy ? (
        <div className="rounded-xl border border-[#c0892e]/20 bg-[#c0892e]/5 px-4 py-3 flex items-center gap-2">
          <svg className="animate-spin h-4 w-4 text-[#c0892e] flex-shrink-0" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
          </svg>
          <span className="text-sm text-[#c0892e]">{STATUS_LABELS[status]}</span>
        </div>
      ) : (
        <button
          onClick={handleGenerate}
          disabled={!valid}
          className="w-full rounded-xl bg-[#c0892e] py-3 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-30"
        >
          <span aria-hidden="true">📝</span> {outputType === "mindmap" ? "Generate Mind Map" : "Generate Summary"}
        </button>
      )}

      {status === "done" && (
        <div className="rounded-xl border border-[#c0892e]/20 bg-[#c0892e]/5 px-4 py-3 text-sm text-[#c0892e] font-medium">
          ✓ {outputType === "mindmap" ? "Mind map ready" : "Summary ready"} — see the list on the right!
        </div>
      )}
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
