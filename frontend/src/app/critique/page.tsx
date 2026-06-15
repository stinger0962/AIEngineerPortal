"use client";

import { useRef, useState } from "react";
import { ClipboardCheck, Upload, Loader2 } from "lucide-react";
import { extractFile, evaluateEssay } from "@/lib/critique/api";
import type { Evaluation } from "@/lib/critique/api";

// ── Paper type config ─────────────────────────────────────────────────────────

const PAPER_TYPES = [
  { value: "research", label: "学术/研究" },
  { value: "argument", label: "议论文" },
  { value: "statement", label: "个人陈述" },
] as const;

type PaperType = (typeof PAPER_TYPES)[number]["value"];

// ── Score bar ─────────────────────────────────────────────────────────────────

function ScoreBar({ score }: { score: number }) {
  return (
    <div className="h-1.5 w-full rounded-full bg-ink/10 overflow-hidden">
      <div
        className="h-full rounded-full bg-gradient-to-r from-[#7fcab9] to-[#5fb3a3] transition-all duration-700"
        style={{ width: `${score * 10}%` }}
      />
    </div>
  );
}

// ── Dimension card ────────────────────────────────────────────────────────────

function DimensionCard({
  label,
  score,
  critique,
  suggestions,
}: {
  label: string;
  score: number;
  critique: string;
  suggestions: string[];
}) {
  return (
    <div className="rounded-[16px] border border-ink/10 bg-white/60 p-4 space-y-3">
      {/* Header row */}
      <div className="flex items-center justify-between gap-2">
        <span className="font-medium text-ink text-sm">{label}</span>
        <span className="text-sm font-semibold tabular-nums" style={{ color: "#5fb3a3" }}>
          {score}/10
        </span>
      </div>

      {/* Score bar */}
      <ScoreBar score={score} />

      {/* Critique */}
      <p className="text-sm leading-6 text-ink/75">{critique}</p>

      {/* Suggestions */}
      {suggestions.length > 0 && (
        <ul className="space-y-1.5">
          {suggestions.map((s, i) => (
            <li key={i} className="flex gap-2 text-[13px] text-ink/70 leading-5">
              <span className="shrink-0 font-semibold" style={{ color: "#5fb3a3" }}>
                →
              </span>
              <span>{s}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ── Results panel ─────────────────────────────────────────────────────────────

function ResultsPanel({ result }: { result: Evaluation | null }) {
  if (!result) {
    return (
      <div className="flex h-full min-h-[320px] items-center justify-center rounded-[28px] border border-ink/10 bg-white/85 shadow-panel">
        <p className="text-center text-sm text-ink/40 px-8 leading-7">
          贴入论文后点「评估」，
          <br />
          这里会显示逐维度诊断
        </p>
      </div>
    );
  }

  const { overall, dimensions } = result;

  return (
    <div className="rounded-[28px] border border-ink/10 bg-white/85 shadow-panel p-6 space-y-6">
      {/* Overall block */}
      <div className="space-y-4">
        {/* Band pill + summary */}
        <div className="flex items-start gap-3 flex-wrap">
          <span
            className="inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold tracking-wide"
            style={{
              background: "rgba(95,179,163,0.12)",
              color: "#3f8a7d",
              border: "1px solid rgba(95,179,163,0.25)",
            }}
          >
            {overall.band}
          </span>
        </div>
        <p className="text-sm leading-7 text-ink/80">{overall.summary}</p>

        {/* Top-fix callout */}
        <div
          className="rounded-xl p-4 space-y-1"
          style={{
            background: "rgba(95,179,163,0.08)",
            border: "1px solid rgba(95,179,163,0.20)",
          }}
        >
          <p
            className="text-[10px] font-semibold uppercase tracking-[0.28em]"
            style={{ color: "#5fb3a3" }}
          >
            最值得先改的一件事
          </p>
          <p className="text-sm leading-6 text-ink/80">{overall.top_fix}</p>
        </div>
      </div>

      {/* Divider */}
      <div className="border-t border-ink/8" />

      {/* Section label */}
      <p
        className="text-[10px] font-semibold uppercase tracking-[0.28em]"
        style={{ color: "#5fb3a3" }}
      >
        各维度评分
      </p>

      {/* Dimensions */}
      <div className="space-y-3">
        {dimensions.map((dim, i) => (
          <DimensionCard key={i} {...dim} />
        ))}
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function CritiquePage() {
  const [paperType, setPaperType] = useState<PaperType>("research");
  const [text, setText] = useState("");
  const [filename, setFilename] = useState<string | null>(null);
  const [extracting, setExtracting] = useState(false);
  const [extractError, setExtractError] = useState<string | null>(null);
  const [evaluating, setEvaluating] = useState(false);
  const [evalError, setEvalError] = useState<string | null>(null);
  const [result, setResult] = useState<Evaluation | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const charCount = text.length;
  const canEvaluate = charCount >= 200 && !evaluating;

  // ── Handlers ──────────────────────────────────────────────────────────────

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    setExtractError(null);
    setExtracting(true);
    try {
      const { text: extracted, filename: name } = await extractFile(file);
      setText(extracted);
      setFilename(name);
    } catch (err) {
      setExtractError(err instanceof Error ? err.message : "解析失败");
    } finally {
      setExtracting(false);
      // Reset file input so the same file can be re-selected
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function handleEvaluate() {
    if (!canEvaluate) return;
    setEvalError(null);
    setEvaluating(true);
    try {
      const evaluation = await evaluateEssay(text, paperType);
      setResult(evaluation);
    } catch (err) {
      setEvalError(err instanceof Error ? err.message : "评估失败");
    } finally {
      setEvaluating(false);
    }
  }

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-6">
      {/* ── Page header ── */}
      <div className="flex items-start gap-4">
        {/* Icon chip */}
        <div
          className="shrink-0 flex items-center justify-center rounded-[16px]"
          style={{
            width: 52,
            height: 52,
            background:
              "linear-gradient(135deg, #7fcab9 0%, #5fb3a3 50%, #3f8a7d 100%)",
          }}
        >
          <ClipboardCheck size={24} color="white" strokeWidth={2} />
        </div>

        {/* Title block */}
        <div className="space-y-1">
          <p
            className="text-xs font-semibold uppercase tracking-[0.28em]"
            style={{ color: "#5fb3a3" }}
          >
            评审 · Critique
          </p>
          <h1 className="font-display text-2xl text-ink leading-tight">
            论文评审{" "}
            <span className="text-ink/40 font-normal">Critique</span>
          </h1>
          <p className="text-sm text-ink/55 leading-6">
            贴入或上传论文，按维度拿到诊断与可执行的修改建议。
          </p>
        </div>
      </div>

      {/* ── Two-column layout ── */}
      <div className="grid gap-6 lg:grid-cols-[1fr_1fr]">
        {/* ── LEFT: Input panel ── */}
        <div className="rounded-[28px] border border-ink/10 bg-white/85 shadow-panel p-6 space-y-5">
          {/* Paper type selector */}
          <div className="space-y-2">
            <p className="text-[10px] font-semibold uppercase tracking-[0.28em] text-ink/45">
              论文类型
            </p>
            <div className="flex gap-2 flex-wrap">
              {PAPER_TYPES.map(({ value, label }) => {
                const active = paperType === value;
                return (
                  <button
                    key={value}
                    onClick={() => setPaperType(value)}
                    className="rounded-full px-4 py-1.5 text-xs font-semibold transition-all"
                    style={
                      active
                        ? {
                            background: "rgba(95,179,163,0.12)",
                            color: "#3f8a7d",
                            border: "1px solid rgba(95,179,163,0.35)",
                          }
                        : {
                            background: "transparent",
                            color: "rgba(20,33,61,0.50)",
                            border: "1px solid rgba(20,33,61,0.12)",
                          }
                    }
                  >
                    {label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Textarea */}
          <div className="space-y-2">
            <p className="text-[10px] font-semibold uppercase tracking-[0.28em] text-ink/45">
              论文全文
            </p>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="粘贴论文全文…（至少约 200 字）"
              className="w-full resize-y rounded-[16px] border border-ink/10 bg-white/70 p-4 text-sm text-ink placeholder:text-ink/35 focus:outline-none focus:ring-2 focus:ring-[#5fb3a3]/40 leading-6"
              style={{ minHeight: 320 }}
            />
            {/* Char counter */}
            <p className="text-right text-xs text-ink/40 tabular-nums">
              {charCount} 字
            </p>
          </div>

          {/* Upload control */}
          <div className="space-y-2">
            <p className="text-[10px] font-semibold uppercase tracking-[0.28em] text-ink/45">
              上传文件
            </p>
            <label
              className="flex cursor-pointer items-center gap-3 rounded-[16px] border border-dashed border-ink/20 bg-white/40 px-4 py-3 transition-colors hover:bg-white/60 hover:border-ink/30"
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".docx,.pdf,.md,.markdown,.txt"
                className="sr-only"
                onChange={handleFileChange}
                disabled={extracting}
              />
              {extracting ? (
                <>
                  <Loader2 size={16} className="animate-spin text-ink/40" />
                  <span className="text-sm text-ink/55">解析中…</span>
                </>
              ) : (
                <>
                  <Upload size={16} className="text-ink/40" />
                  <span className="text-sm text-ink/55">
                    {filename
                      ? <><span className="font-medium text-ink/70">{filename}</span><span className="text-ink/40"> · 点击更换</span></>
                      : ".docx · .pdf · .md · .txt"}
                  </span>
                </>
              )}
            </label>

            {/* Extract error */}
            {extractError && (
              <p className="rounded-xl bg-red-50 border border-red-200 px-4 py-2.5 text-xs text-red-600">
                {extractError}
              </p>
            )}
          </div>

          {/* Evaluate button */}
          <button
            onClick={handleEvaluate}
            disabled={!canEvaluate}
            className="flex w-full items-center justify-center gap-2 rounded-[16px] py-3 text-sm font-semibold text-white transition-all"
            style={{
              background: canEvaluate
                ? "linear-gradient(135deg, #7fcab9 0%, #5fb3a3 50%, #3f8a7d 100%)"
                : "rgba(20,33,61,0.08)",
              color: canEvaluate ? "white" : "rgba(20,33,61,0.30)",
              cursor: canEvaluate ? "pointer" : "not-allowed",
            }}
          >
            {evaluating ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                评估中…（约 10–30 秒）
              </>
            ) : (
              "评估 Evaluate"
            )}
          </button>

          {/* Eval error */}
          {evalError && (
            <p className="rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-xs text-red-600">
              {evalError}
            </p>
          )}
        </div>

        {/* ── RIGHT: Results panel ── */}
        <div>
          <ResultsPanel result={result} />
        </div>
      </div>
    </div>
  );
}
