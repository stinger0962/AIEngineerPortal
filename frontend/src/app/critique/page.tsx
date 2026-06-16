"use client";

import { useRef, useState } from "react";
import { ClipboardCheck, Upload, Loader2 } from "lucide-react";
import { extractFile, evaluateEssay, reviseEssay, docReview as callDocReview } from "@/lib/critique/api";
import type { Evaluation, Revision, DocReview, Finding } from "@/lib/critique/api";

// ── Paper type config ─────────────────────────────────────────────────────────

const PAPER_TYPES = [
  { value: "research", label: "学术/研究" },
  { value: "argument", label: "议论文" },
  { value: "statement", label: "个人陈述" },
] as const;

type PaperType = (typeof PAPER_TYPES)[number]["value"];

// ── Output language config ────────────────────────────────────────────────────

const OUTPUT_LANGS = [
  { value: "zh", label: "中文" },
  { value: "en", label: "English" },
  { value: "auto", label: "跟随原文" },
] as const;

type OutputLang = (typeof OUTPUT_LANGS)[number]["value"];

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

// ── Doc-review severity pill styles ──────────────────────────────────────────

function severityStyle(severity: string): React.CSSProperties {
  if (severity === "高") {
    return { background: "rgba(163,50,45,0.10)", color: "#a3322d", border: "1px solid rgba(163,50,45,0.25)" };
  }
  if (severity === "中") {
    return { background: "rgba(160,106,48,0.10)", color: "#a06a30", border: "1px solid rgba(160,106,48,0.25)" };
  }
  // 低 or unknown
  return { background: "rgba(20,33,61,0.08)", color: "rgba(20,33,61,0.55)", border: "1px solid rgba(20,33,61,0.15)" };
}

// ── Finding card ──────────────────────────────────────────────────────────────

function FindingCard({ finding }: { finding: Finding }) {
  return (
    <div className="bg-white border border-ink/10 rounded-xl p-4 space-y-2.5">
      {/* Top row: severity pill + category chip */}
      <div className="flex flex-wrap items-center gap-2">
        <span
          className="inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-semibold"
          style={severityStyle(finding.severity)}
        >
          {finding.severity || "低"}
        </span>
        <span
          className="inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-medium"
          style={{
            background: "rgba(95,179,163,0.12)",
            color: "#3f8a7d",
          }}
        >
          {finding.category}
        </span>
      </div>

      {/* Location */}
      {finding.location && (
        <p className="font-mono text-[12px] text-ink/50">
          定位：{finding.location}
        </p>
      )}

      {/* Issue */}
      <p className="text-sm leading-6 text-ink/80">{finding.issue}</p>

      {/* Recommendation */}
      <div
        className="rounded-lg p-2.5 text-[13px] text-ink/85"
        style={{
          background: "rgba(95,179,163,0.08)",
          border: "1px solid rgba(95,179,163,0.20)",
        }}
      >
        <span className="font-semibold" style={{ color: "#5fb3a3" }}>→ </span>
        {finding.recommendation}
      </div>
    </div>
  );
}

// ── Doc-review results panel ──────────────────────────────────────────────────

function DocReviewPanel({ review }: { review: DocReview }) {
  return (
    <div className="rounded-[28px] border border-ink/10 bg-white/85 shadow-panel p-6 space-y-5">
      {/* Section header */}
      <div className="space-y-1.5">
        <p
          className="text-[10px] font-semibold uppercase tracking-[0.28em]"
          style={{ color: "#5fb3a3" }}
        >
          文档审阅 · Doc review
        </p>
        <p className="text-sm leading-6 text-ink/75">{review.summary}</p>
      </div>

      <div className="border-t border-ink/8" />

      {/* Findings list */}
      {review.findings.length === 0 ? (
        <p className="text-sm text-ink/50 leading-6">未发现明显的文档级问题。</p>
      ) : (
        <div className="space-y-3">
          {review.findings.map((f, i) => (
            <FindingCard key={i} finding={f} />
          ))}
        </div>
      )}
    </div>
  );
}

// ── Results panel ─────────────────────────────────────────────────────────────

type ResultsPanelProps = {
  result: Evaluation | null;
  onRevise: () => void;
  revising: boolean;
  reviseError: string | null;
  revision: Revision | null;
  originalSnapshot: string;
  onAdopt: (revised: string) => void;
};

function ResultsPanel({
  result,
  onRevise,
  revising,
  reviseError,
  revision,
  originalSnapshot,
  onAdopt,
}: ResultsPanelProps) {
  const [copied, setCopied] = useState(false);

  async function handleCopy(text: string) {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      // clipboard not available; silently ignore
    }
  }

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

      {/* Divider before revise */}
      <div className="border-t border-ink/8" />

      {/* ── Revise button ── */}
      <button
        onClick={onRevise}
        disabled={revising}
        className="flex w-full items-center justify-center gap-2 rounded-[16px] py-3 text-sm font-semibold transition-all"
        style={{
          background: revising
            ? "rgba(20,33,61,0.08)"
            : "rgba(95,179,163,0.12)",
          color: revising ? "rgba(20,33,61,0.30)" : "#3f8a7d",
          border: revising
            ? "1px solid rgba(20,33,61,0.10)"
            : "1px solid rgba(95,179,163,0.35)",
          cursor: revising ? "not-allowed" : "pointer",
        }}
      >
        {revising ? (
          <>
            <Loader2 size={15} className="animate-spin" />
            改进中…（约 20–40 秒）
          </>
        ) : (
          "改进这一版 Revise"
        )}
      </button>

      {/* Revise error */}
      {reviseError && (
        <p className="rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-xs text-red-600">
          {reviseError}
        </p>
      )}

      {/* ── Revision block ── */}
      {revision && (
        <div className="space-y-5">
          {/* Verdict pill + reason */}
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              {revision.verdict.better ? (
                <span
                  className="inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold"
                  style={{
                    background: "rgba(31,122,77,0.10)",
                    color: "#1f7a4d",
                    border: "1px solid rgba(31,122,77,0.25)",
                  }}
                >
                  改后更好 ✓
                </span>
              ) : (
                <span
                  className="inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold"
                  style={{
                    background: "rgba(160,106,48,0.10)",
                    color: "#a06a30",
                    border: "1px solid rgba(160,106,48,0.25)",
                  }}
                >
                  未必更好 · 谨慎采纳
                </span>
              )}
            </div>
            <p className="text-sm text-ink/70 leading-6">{revision.verdict.reason}</p>
            {revision.verdict.dimensions_improved.length > 0 && (
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="text-xs text-ink/45">提升：</span>
                {revision.verdict.dimensions_improved.map((d, i) => (
                  <span
                    key={i}
                    className="rounded-full px-2.5 py-0.5 text-xs"
                    style={{
                      background: "rgba(95,179,163,0.10)",
                      color: "#3f8a7d",
                      border: "1px solid rgba(95,179,163,0.25)",
                    }}
                  >
                    {d}
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Changes list */}
          {revision.changes.length > 0 && (
            <div className="space-y-2">
              <p
                className="text-[10px] font-semibold uppercase tracking-[0.28em]"
                style={{ color: "#5fb3a3" }}
              >
                这轮改了什么
              </p>
              <ul className="space-y-1.5">
                {revision.changes.map((c, i) => (
                  <li key={i} className="flex gap-2 text-[13px] text-ink/75 leading-5">
                    <span className="shrink-0 font-semibold" style={{ color: "#5fb3a3" }}>
                      →
                    </span>
                    <span>{c}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Side-by-side comparison */}
          <div className="space-y-2">
            <p
              className="text-[10px] font-semibold uppercase tracking-[0.28em]"
              style={{ color: "#5fb3a3" }}
            >
              并排对照
            </p>
            <div className="grid lg:grid-cols-2 gap-3">
              {/* Original */}
              <div className="space-y-1.5">
                <p className="text-xs font-medium text-ink/50">原文</p>
                <div
                  className="max-h-[420px] overflow-auto rounded-xl border border-ink/10 bg-white p-4 text-[13px] leading-6 whitespace-pre-wrap text-ink/80"
                >
                  {originalSnapshot}
                </div>
              </div>
              {/* Revised */}
              <div className="space-y-1.5">
                <p className="text-xs font-medium text-ink/50">改后</p>
                <div
                  className="max-h-[420px] overflow-auto rounded-xl border border-ink/10 bg-white p-4 text-[13px] leading-6 whitespace-pre-wrap text-ink/80"
                >
                  {revision.revised}
                </div>
              </div>
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex flex-wrap gap-3">
            {/* 采纳改后 */}
            <button
              onClick={() => onAdopt(revision.revised)}
              className="rounded-[14px] px-5 py-2.5 text-sm font-semibold transition-all"
              style={{
                background: "linear-gradient(135deg, #7fcab9 0%, #5fb3a3 50%, #3f8a7d 100%)",
                color: "white",
              }}
            >
              采纳改后
            </button>
            {/* 复制改后 */}
            <button
              onClick={() => handleCopy(revision.revised)}
              className="rounded-[14px] px-5 py-2.5 text-sm font-semibold transition-all"
              style={{
                background: "transparent",
                color: "#3f8a7d",
                border: "1px solid rgba(95,179,163,0.40)",
              }}
            >
              {copied ? "已复制" : "复制改后"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function CritiquePage() {
  const [paperType, setPaperType] = useState<PaperType>("research");
  const [outputLang, setOutputLang] = useState<OutputLang>("auto");
  const [text, setText] = useState("");
  const [filename, setFilename] = useState<string | null>(null);
  const [extracting, setExtracting] = useState(false);
  const [extractError, setExtractError] = useState<string | null>(null);
  const [evaluating, setEvaluating] = useState(false);
  const [evalError, setEvalError] = useState<string | null>(null);
  const [result, setResult] = useState<Evaluation | null>(null);

  // Revise state
  const [revising, setRevising] = useState(false);
  const [reviseError, setReviseError] = useState<string | null>(null);
  const [revision, setRevision] = useState<Revision | null>(null);
  const [originalSnapshot, setOriginalSnapshot] = useState("");

  // Doc-review state
  const [docReviewing, setDocReviewing] = useState(false);
  const [docReviewError, setDocReviewError] = useState<string | null>(null);
  const [docReviewResult, setDocReviewResult] = useState<DocReview | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const charCount = text.length;
  const canEvaluate = charCount >= 200 && !evaluating;
  const canDocReview = charCount >= 200 && !docReviewing && !evaluating;

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
    // Clear any prior revision and doc-review when re-evaluating
    setRevision(null);
    setReviseError(null);
    setDocReviewResult(null);
    setDocReviewError(null);
    try {
      const evaluation = await evaluateEssay(text, paperType, outputLang);
      setResult(evaluation);
    } catch (err) {
      setEvalError(err instanceof Error ? err.message : "评估失败");
    } finally {
      setEvaluating(false);
    }
  }

  async function handleDocReview() {
    if (!canDocReview) return;
    setDocReviewError(null);
    setDocReviewResult(null);
    setDocReviewing(true);
    try {
      const review = await callDocReview(text, paperType, outputLang);
      setDocReviewResult(review);
    } catch (err) {
      setDocReviewError(err instanceof Error ? err.message : "审阅失败");
    } finally {
      setDocReviewing(false);
    }
  }

  async function handleRevise() {
    if (revising) return;
    setReviseError(null);
    setRevision(null);
    // Snapshot the textarea content at the moment of clicking revise
    const snapshot = text;
    setOriginalSnapshot(snapshot);
    setRevising(true);
    try {
      const rev = await reviseEssay(snapshot, paperType, outputLang);
      setRevision(rev);
    } catch (err) {
      setReviseError(err instanceof Error ? err.message : "改进失败");
    } finally {
      setRevising(false);
    }
  }

  function handleAdopt(revised: string) {
    setText(revised);
    // Clear eval + revision + doc-review so user is prompted to re-evaluate
    setResult(null);
    setRevision(null);
    setReviseError(null);
    setDocReviewResult(null);
    setDocReviewError(null);
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

          {/* Output language selector */}
          <div className="space-y-2">
            <p className="text-[10px] font-semibold uppercase tracking-[0.28em] text-ink/45">
              输出语言
            </p>
            <div className="flex gap-2 flex-wrap">
              {OUTPUT_LANGS.map(({ value, label }) => {
                const active = outputLang === value;
                return (
                  <button
                    key={value}
                    onClick={() => setOutputLang(value)}
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

          {/* Action buttons row */}
          <div className="space-y-3">
            {/* Primary: Evaluate */}
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

            {/* Secondary: Doc review */}
            <button
              onClick={handleDocReview}
              disabled={!canDocReview}
              className="flex w-full items-center justify-center gap-2 rounded-[16px] py-3 text-sm font-semibold transition-all"
              style={{
                background: "transparent",
                color: canDocReview ? "#3f8a7d" : "rgba(20,33,61,0.28)",
                border: canDocReview
                  ? "1px solid rgba(95,179,163,0.45)"
                  : "1px solid rgba(20,33,61,0.10)",
                cursor: canDocReview ? "pointer" : "not-allowed",
              }}
            >
              {docReviewing ? (
                <>
                  <Loader2 size={15} className="animate-spin" />
                  审阅中…（约 20–40 秒，长文更久）
                </>
              ) : (
                "文档审阅 Doc review"
              )}
            </button>

            {/* Helper text */}
            <p className="text-[11px] text-ink/40 leading-5 text-center">
              文档审阅生成可在自己编辑器中执行的修改清单，不重写文件。
            </p>
          </div>

          {/* Eval error */}
          {evalError && (
            <p className="rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-xs text-red-600">
              {evalError}
            </p>
          )}

          {/* Doc-review error */}
          {docReviewError && (
            <p className="rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-xs text-red-600">
              {docReviewError}
            </p>
          )}
        </div>

        {/* ── RIGHT: Results panel ── */}
        <div className="space-y-6">
          {/* Doc-review results (shown when present; replaces placeholder) */}
          {docReviewResult ? (
            <DocReviewPanel review={docReviewResult} />
          ) : (
            <ResultsPanel
              result={result}
              onRevise={handleRevise}
              revising={revising}
              reviseError={reviseError}
              revision={revision}
              originalSnapshot={originalSnapshot}
              onAdopt={handleAdopt}
            />
          )}
          {/* If both doc-review AND evaluation results exist, show eval below */}
          {docReviewResult && result && (
            <ResultsPanel
              result={result}
              onRevise={handleRevise}
              revising={revising}
              reviseError={reviseError}
              revision={revision}
              originalSnapshot={originalSnapshot}
              onAdopt={handleAdopt}
            />
          )}
        </div>
      </div>
    </div>
  );
}
