"use client";

import { Fragment, useRef, useState } from "react";
import { ClipboardCheck, Upload, Loader2, Sparkles, FileSearch, Compass } from "lucide-react";
import {
  extractFile,
  evaluateEssay,
  patchEssay,
  docReview as callDocReview,
  probeEssay,
  integrateAnswers,
} from "@/lib/critique/api";
import type {
  Evaluation,
  PatchEdit,
  DocReview,
  Finding,
  Dimension,
  ProbeQuestion,
  ProbeStance,
} from "@/lib/critique/api";

// ── Accents ─────────────────────────────────────────────────────────────────
const WRITING = "#5fb3a3"; // 写作层 — celadon (AI 可代改)
const WRITING_DARK = "#3f8a7d";
const SUBSTANCE = "#b07d2e"; // 实质层 — copper/amber (需作者补料)
const SUBSTANCE_DARK = "#9a6a30";

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

function ScoreBar({ score, accent = WRITING }: { score: number; accent?: string }) {
  return (
    <div className="h-1.5 w-full rounded-full bg-ink/10 overflow-hidden">
      <div
        className="h-full rounded-full transition-all duration-700"
        style={{ width: `${score * 10}%`, background: accent }}
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
  accent = WRITING,
}: {
  label: string;
  score: number;
  critique: string;
  suggestions: string[];
  accent?: string;
}) {
  return (
    <div className="rounded-[16px] border border-ink/10 bg-white/60 p-4 space-y-3">
      {/* Header row */}
      <div className="flex items-center justify-between gap-2">
        <span className="font-medium text-ink text-sm">{label}</span>
        <span className="text-sm font-semibold tabular-nums" style={{ color: accent }}>
          {score}/10
        </span>
      </div>

      {/* Score bar */}
      <ScoreBar score={score} accent={accent} />

      {/* Critique */}
      <p className="text-sm leading-6 text-ink/75">{critique}</p>

      {/* Suggestions */}
      {suggestions.length > 0 && (
        <ul className="space-y-1.5">
          {suggestions.map((s, i) => (
            <li key={i} className="flex gap-2 text-[13px] text-ink/70 leading-5">
              <span className="shrink-0 font-semibold" style={{ color: accent }}>
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
    <div className="space-y-4">
      <p className="text-sm leading-6 text-ink/75">{review.summary}</p>

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

// ── Patch edit diff card ──────────────────────────────────────────────────────

function PatchEditCard({ edit, variant = "applied" }: { edit: PatchEdit; variant?: "applied" | "unapplied" }) {
  const borderColor = variant === "unapplied" ? "rgba(160,106,48,0.30)" : "rgba(20,33,61,0.10)";
  return (
    <div
      className="rounded-xl p-3 space-y-1.5"
      style={{
        background: "#fff",
        border: `1px solid ${borderColor}`,
      }}
    >
      {/* find — strikethrough red */}
      <p
        className="text-[13px] leading-5 line-through break-words"
        style={{ color: "#a3322d", background: "rgba(163,50,45,0.06)", borderRadius: 4, padding: "2px 4px" }}
      >
        {edit.find}
      </p>
      {/* replace — green */}
      <p
        className="text-[13px] leading-5 break-words"
        style={{ color: "#1f7a4d", background: "rgba(31,122,77,0.08)", borderRadius: 4, padding: "2px 4px" }}
      >
        {edit.replace}
      </p>
      {/* reason */}
      {edit.reason && (
        <p className="text-[12px] leading-5 text-ink/55">{edit.reason}</p>
      )}
    </div>
  );
}

// ── Improvement worktop ───────────────────────────────────────────────────────
// One evolving draft that BOTH 改写作 (writing) and 深挖融入 (substance) edit in
// place — they stack onto the same text instead of producing two rival results.

type WorkEntry = {
  source: "writing" | "substance";
  summary: string;
  applied: PatchEdit[];
  unapplied: PatchEdit[];
  notes: string[];
};

function WorkLogGroup({
  title,
  count,
  accent,
  edits,
}: {
  title: string;
  count: number;
  accent: string;
  edits: PatchEdit[];
}) {
  return (
    <details className="rounded-xl border border-ink/10 bg-white/70">
      <summary className="flex cursor-pointer list-none items-center gap-2 px-3 py-2.5 text-[13px]">
        <span className="font-semibold" style={{ color: accent }}>{title}</span>
        <span className="text-ink/45">{count} 处</span>
        <span className="ml-auto text-ink/35 text-[11px]">展开查看</span>
      </summary>
      <div className="space-y-2 px-3 pb-3">
        {edits.map((edit, i) => (
          <PatchEditCard key={i} edit={edit} variant="applied" />
        ))}
      </div>
    </details>
  );
}

function WorktopPanel({
  draft,
  worklog,
  busy,
  onAdopt,
  onReset,
}: {
  draft: string;
  worklog: WorkEntry[];
  busy: boolean;
  onAdopt: (text: string) => void;
  onReset: () => void;
}) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(draft);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      /* clipboard unavailable */
    }
  }

  function handleDownload() {
    const blob = new Blob([draft], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "improved.md";
    a.click();
    URL.revokeObjectURL(url);
  }

  const writingEdits = worklog.filter((e) => e.source === "writing").flatMap((e) => e.applied);
  const substanceEdits = worklog.filter((e) => e.source === "substance").flatMap((e) => e.applied);
  const allUnapplied = worklog.flatMap((e) => e.unapplied);
  const allNotes = worklog.flatMap((e) => e.notes);

  return (
    <div
      className="rounded-[20px] p-5 space-y-4"
      style={{ background: "rgba(95,179,163,0.05)", border: `2px solid ${WRITING}` }}
    >
      {/* Header */}
      <div className="flex items-center gap-2">
        <span className="text-base font-semibold text-ink">改进工作稿</span>
        <span className="ml-auto text-[11px] text-ink/45">写作 + 实质 已叠加</span>
      </div>

      {/* Edit log, grouped by source */}
      <div className="space-y-2">
        <p className="text-[10px] font-semibold uppercase tracking-[0.28em] text-ink/45">已做的改进</p>
        {writingEdits.length > 0 && (
          <WorkLogGroup title="写作改进" count={writingEdits.length} accent={WRITING_DARK} edits={writingEdits} />
        )}
        {substanceEdits.length > 0 && (
          <WorkLogGroup title="实质融入" count={substanceEdits.length} accent={SUBSTANCE_DARK} edits={substanceEdits} />
        )}
        {writingEdits.length === 0 && substanceEdits.length === 0 && (
          <p className="text-xs text-ink/45">本轮没有可自动套用的精确编辑（见下方需手动建议）。</p>
        )}
      </div>

      {/* Unapplied */}
      {allUnapplied.length > 0 && (
        <div
          className="rounded-xl p-4 space-y-2"
          style={{ background: "rgba(160,106,48,0.06)", border: "1px solid rgba(160,106,48,0.22)" }}
        >
          <p className="text-[10px] font-semibold uppercase tracking-[0.28em]" style={{ color: "#a06a30" }}>
            未能自动定位 ({allUnapplied.length}) · 请手动处理
          </p>
          <div className="space-y-2">
            {allUnapplied.map((edit, i) => (
              <PatchEditCard key={i} edit={edit} variant="unapplied" />
            ))}
          </div>
        </div>
      )}

      {/* Notes */}
      {allNotes.length > 0 && (
        <div className="space-y-2">
          <p className="text-[10px] font-semibold uppercase tracking-[0.28em]" style={{ color: WRITING }}>
            建议（需手动）
          </p>
          <ul className="space-y-1.5">
            {allNotes.map((note, i) => (
              <li key={i} className="flex gap-2 text-[13px] text-ink/75 leading-5">
                <span className="shrink-0 font-semibold" style={{ color: WRITING }}>→</span>
                <span>{note}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Full draft */}
      <div className="space-y-2">
        <p className="text-[10px] font-semibold uppercase tracking-[0.28em]" style={{ color: WRITING }}>
          改后全文
        </p>
        <div className="max-h-[420px] overflow-auto bg-white border border-ink/10 rounded-xl p-4 text-[13px] leading-6 whitespace-pre-wrap text-ink/80">
          {draft}
        </div>
      </div>

      {/* Single action bar */}
      <div className="flex flex-wrap items-center gap-3">
        <button
          onClick={() => onAdopt(draft)}
          disabled={busy}
          className="rounded-[14px] px-5 py-2.5 text-sm font-semibold transition-all"
          style={{
            background: busy ? "rgba(20,33,61,0.08)" : "linear-gradient(135deg, #7fcab9 0%, #5fb3a3 50%, #3f8a7d 100%)",
            color: busy ? "rgba(20,33,61,0.30)" : "white",
            cursor: busy ? "not-allowed" : "pointer",
          }}
        >
          采纳为新原文并重新诊断
        </button>
        <button
          onClick={handleCopy}
          className="rounded-[14px] px-5 py-2.5 text-sm font-semibold transition-all"
          style={{ background: "transparent", color: WRITING_DARK, border: "1px solid rgba(95,179,163,0.40)" }}
        >
          {copied ? "已复制" : "复制"}
        </button>
        <button
          onClick={handleDownload}
          className="rounded-[14px] px-5 py-2.5 text-sm font-semibold transition-all"
          style={{ background: "transparent", color: "rgba(20,33,61,0.55)", border: "1px solid rgba(20,33,61,0.15)" }}
        >
          下载 .md
        </button>
        <button
          onClick={onReset}
          disabled={busy}
          className="ml-auto rounded-[14px] px-3 py-2.5 text-[13px] font-medium transition-all"
          style={{ background: "transparent", color: "rgba(20,33,61,0.45)", cursor: busy ? "not-allowed" : "pointer" }}
        >
          重置工作稿
        </button>
      </div>
    </div>
  );
}

// ── Progress rail ─────────────────────────────────────────────────────────────

type StepState = "done" | "active" | "todo" | "soon";

function ProgressRail({ steps }: { steps: { label: string; state: StepState }[] }) {
  return (
    <div className="flex items-center gap-1.5">
      {steps.map((s, i) => {
        let circle: React.CSSProperties;
        let labelColor: string;
        let labelWeight = 500;
        if (s.state === "done") {
          circle = { background: WRITING, color: "#fff" };
          labelColor = "rgba(20,33,61,0.70)";
        } else if (s.state === "active") {
          circle = { background: "rgba(95,179,163,0.16)", color: WRITING_DARK, border: `1.5px solid ${WRITING}` };
          labelColor = WRITING_DARK;
          labelWeight = 600;
        } else if (s.state === "soon") {
          circle = { background: "rgba(160,106,48,0.10)", color: SUBSTANCE_DARK, border: "1px dashed rgba(160,106,48,0.45)" };
          labelColor = SUBSTANCE_DARK;
        } else {
          circle = { background: "rgba(20,33,61,0.07)", color: "rgba(20,33,61,0.32)" };
          labelColor = "rgba(20,33,61,0.32)";
        }
        return (
          <Fragment key={s.label}>
            {i > 0 && (
              <div className="h-px flex-1 min-w-[8px]" style={{ background: "rgba(20,33,61,0.12)" }} />
            )}
            <div className="flex items-center gap-1.5 shrink-0">
              <span
                className="flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold"
                style={circle}
              >
                {s.state === "done" ? "✓" : i + 1}
              </span>
              <span className="text-[11px]" style={{ color: labelColor, fontWeight: labelWeight }}>
                {s.label}
                {s.state === "soon" && <span className="text-[9px]"> · 即将</span>}
              </span>
            </div>
          </Fragment>
        );
      })}
    </div>
  );
}

// ── Layer section header ──────────────────────────────────────────────────────

function LayerHeader({
  title,
  badge,
  accent,
  subtitle,
}: {
  title: string;
  badge: string;
  accent: string;
  subtitle: string;
}) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-2">
        <span className="text-base font-semibold text-ink">{title}</span>
        <span
          className="rounded-full px-2.5 py-0.5 text-[10px] font-semibold"
          style={{ background: `${accent}1f`, color: accent, border: `1px solid ${accent}40` }}
        >
          {badge}
        </span>
      </div>
      <p className="text-[12px] leading-5 text-ink/50">{subtitle}</p>
    </div>
  );
}

// ── Deep-dive (Socratic substance) panel ─────────────────────────────────────

const STANCES: { value: ProbeStance; label: string }[] = [
  { value: "evidence", label: "我有数据·引用" },
  { value: "speculation", label: "只是推测" },
  { value: "skip", label: "暂时跳过" },
];

type DeepDiveAnswer = { answer: string; stance: ProbeStance };

function DeepDivePanel({
  questions,
  integrating,
  integrateError,
  integratedCount,
  onIntegrate,
  onReprobe,
}: {
  questions: ProbeQuestion[];
  integrating: boolean;
  integrateError: string | null;
  integratedCount: number;
  onIntegrate: (answers: { question: string; answer: string; stance: ProbeStance }[]) => void;
  onReprobe: () => void;
}) {
  const [answers, setAnswers] = useState<Record<number, DeepDiveAnswer>>(() =>
    Object.fromEntries(questions.map((_, i) => [i, { answer: "", stance: "evidence" as ProbeStance }])),
  );

  const setText = (i: number, answer: string) =>
    setAnswers((prev) => ({ ...prev, [i]: { ...prev[i], answer } }));
  const setStance = (i: number, stance: ProbeStance) =>
    setAnswers((prev) => ({ ...prev, [i]: { ...prev[i], stance } }));

  const canIntegrate =
    !integrating &&
    questions.some((_, i) => answers[i].stance !== "skip" && answers[i].answer.trim().length > 0);

  function handleIntegrate() {
    if (!canIntegrate) return;
    onIntegrate(
      questions.map((q, i) => ({
        question: q.question,
        answer: answers[i].answer,
        stance: answers[i].stance,
      })),
    );
  }

  return (
    <div className="space-y-4">
      {/* Question cards */}
      <div className="space-y-3">
        {questions.map((q, i) => {
          const a = answers[i];
          const isSkip = a.stance === "skip";
          return (
            <div
              key={i}
              className="rounded-[16px] p-4 space-y-3"
              style={{ background: "rgba(176,125,46,0.05)", border: "1px solid rgba(176,125,46,0.22)" }}
            >
              {/* weakness + location */}
              <div className="flex flex-wrap items-center gap-2">
                <span
                  className="inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-semibold"
                  style={{ background: "rgba(176,125,46,0.12)", color: SUBSTANCE_DARK, border: "1px solid rgba(176,125,46,0.30)" }}
                >
                  实质薄弱
                </span>
                {q.location && <span className="font-mono text-[12px] text-ink/45">{q.location}</span>}
              </div>
              {q.weakness && <p className="text-[13px] leading-5 text-ink/60">{q.weakness}</p>}

              {/* question */}
              <p className="text-sm font-medium leading-6 text-ink">{q.question}</p>

              {/* answer textarea */}
              <textarea
                value={a.answer}
                onChange={(e) => setText(i, e.target.value)}
                disabled={isSkip}
                placeholder={
                  isSkip
                    ? "已选择暂时跳过——此处不改动，仅作提醒。"
                    : "补充真实材料：具体数据、文献出处、对照、机制解释…（标『只是推测』则会被弱化处理）"
                }
                className="w-full resize-y rounded-[12px] border border-ink/12 bg-white/75 p-3 text-[13px] leading-6 text-ink placeholder:text-ink/35 focus:outline-none focus:ring-2 disabled:opacity-50 disabled:bg-ink/[0.03]"
                style={{ minHeight: 72, ...( { "--tw-ring-color": "rgba(176,125,46,0.40)" } as React.CSSProperties) }}
              />

              {/* stance chips */}
              <div className="flex flex-wrap gap-2">
                {STANCES.map(({ value, label }) => {
                  const active = a.stance === value;
                  return (
                    <button
                      key={value}
                      onClick={() => setStance(i, value)}
                      className="rounded-full px-3 py-1 text-[11px] font-semibold transition-all"
                      style={
                        active
                          ? { background: "rgba(176,125,46,0.14)", color: SUBSTANCE_DARK, border: "1px solid rgba(176,125,46,0.40)" }
                          : { background: "transparent", color: "rgba(20,33,61,0.45)", border: "1px solid rgba(20,33,61,0.12)" }
                      }
                    >
                      {label}
                    </button>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {/* Integrate / done */}
      {integratedCount > 0 ? (
        <>
          <div
            className="rounded-[14px] px-4 py-3 text-[13px] flex items-center gap-2"
            style={{ background: "rgba(176,125,46,0.10)", color: SUBSTANCE_DARK, border: "1px solid rgba(176,125,46,0.30)" }}
          >
            <Compass size={15} />
            已融入工作稿（{integratedCount} 处）—— 见下方「改进工作稿」。
          </div>
          <button
            onClick={onReprobe}
            disabled={integrating}
            className="flex w-full items-center justify-center gap-2 rounded-[16px] py-2.5 text-[13px] font-medium transition-all"
            style={{
              background: "transparent",
              color: SUBSTANCE_DARK,
              border: "1px solid rgba(176,125,46,0.30)",
              cursor: integrating ? "not-allowed" : "pointer",
            }}
          >
            重新提问（基于当前工作稿）
          </button>
        </>
      ) : (
        <>
          <button
            onClick={handleIntegrate}
            disabled={!canIntegrate}
            className="flex w-full items-center justify-center gap-2 rounded-[16px] py-3 text-sm font-semibold transition-all"
            style={{
              background: canIntegrate ? "rgba(176,125,46,0.12)" : "rgba(20,33,61,0.08)",
              color: canIntegrate ? SUBSTANCE_DARK : "rgba(20,33,61,0.30)",
              border: canIntegrate ? "1px solid rgba(176,125,46,0.38)" : "1px solid rgba(20,33,61,0.10)",
              cursor: canIntegrate ? "pointer" : "not-allowed",
            }}
          >
            {integrating ? (
              <>
                <Loader2 size={15} className="animate-spin" />
                融入中…（据实补强 / 弱化推测，约 20–40 秒）
              </>
            ) : (
              <>
                <Compass size={15} />
                把我的回答融入工作稿
              </>
            )}
          </button>
          <p className="text-[11px] text-ink/40 leading-5 text-center -mt-1">
            AI 只用你给的真材料补强；标「推测」的会被弱化；「跳过」的不动——绝不替你编造。
          </p>
        </>
      )}

      {integrateError && (
        <p className="rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-xs text-red-600">
          {integrateError}
        </p>
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

  // Full-width tabbed layout (not split-screen): 原文 editor ↔ 打磨 flow.
  const [activeTab, setActiveTab] = useState<"source" | "polish">("source");

  // Improvement worktop: one evolving draft + a log of what each op applied.
  // Both 改写作 and 深挖融入 edit `draft` in place and append to `worklog`.
  const [draft, setDraft] = useState<string | null>(null);
  const [worklog, setWorklog] = useState<WorkEntry[]>([]);

  // 改写作 (writing-layer patch) state
  const [improving, setImproving] = useState(false);
  const [improveError, setImproveError] = useState<string | null>(null);

  // Doc-review state
  const [docReviewing, setDocReviewing] = useState(false);
  const [docReviewError, setDocReviewError] = useState<string | null>(null);
  const [docReviewResult, setDocReviewResult] = useState<DocReview | null>(null);

  // Deep-dive (Socratic substance) state
  const [probing, setProbing] = useState(false);
  const [probeError, setProbeError] = useState<string | null>(null);
  const [questions, setQuestions] = useState<ProbeQuestion[] | null>(null);
  const [integrating, setIntegrating] = useState(false);
  const [integrateError, setIntegrateError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const charCount = text.length;
  const hasEnough = charCount >= 200;
  const busy = evaluating || improving || docReviewing || probing || integrating;
  const canEvaluate = hasEnough && !busy;
  const canDocReview = hasEnough && !busy;
  const canImprove = hasEnough && !busy;

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
    // Clear all downstream when re-diagnosing
    setImproveError(null);
    setDocReviewResult(null);
    setDocReviewError(null);
    resetWorktop();
    resetDeepDive();
    try {
      const evaluation = await evaluateEssay(text, paperType, outputLang);
      setResult(evaluation);
      setActiveTab("polish"); // move into the polish flow once diagnosed
    } catch (err) {
      setEvalError(err instanceof Error ? err.message : "诊断失败");
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
      // Review the latest version (the worktop draft if any improvements ran).
      const review = await callDocReview(draft ?? text, paperType, outputLang);
      setDocReviewResult(review);
    } catch (err) {
      setDocReviewError(err instanceof Error ? err.message : "审阅失败");
    } finally {
      setDocReviewing(false);
    }
  }

  // Both improve & integrate edit the SAME evolving draft (current draft, or the
  // original text on the first op) and append what they applied to the worklog.
  async function handleImprove() {
    if (!canImprove) return;
    setImproveError(null);
    setImproving(true);
    try {
      const result = await patchEssay(draft ?? text, paperType, outputLang);
      setDraft(result.patched);
      setWorklog((w) => [
        ...w,
        { source: "writing", summary: result.summary, applied: result.applied, unapplied: result.unapplied, notes: result.notes },
      ]);
    } catch (err) {
      setImproveError(err instanceof Error ? err.message : "改进失败");
    } finally {
      setImproving(false);
    }
  }

  function resetWorktop() {
    setDraft(null);
    setWorklog([]);
    setImproveError(null);
  }

  function resetDeepDive() {
    setQuestions(null);
    setProbeError(null);
    setIntegrateError(null);
  }

  async function handleProbe() {
    if (busy || !hasEnough) return;
    setProbeError(null);
    setQuestions(null);
    setIntegrateError(null);
    setProbing(true);
    try {
      const qs = await probeEssay(draft ?? text, paperType, outputLang);
      setQuestions(qs);
    } catch (err) {
      setProbeError(err instanceof Error ? err.message : "提问失败");
    } finally {
      setProbing(false);
    }
  }

  async function handleIntegrate(
    answers: { question: string; answer: string; stance: ProbeStance }[],
  ) {
    if (busy) return;
    setIntegrateError(null);
    setIntegrating(true);
    try {
      const result = await integrateAnswers(draft ?? text, answers, paperType, outputLang);
      setDraft(result.patched);
      setWorklog((w) => [
        ...w,
        { source: "substance", summary: result.summary, applied: result.applied, unapplied: result.unapplied, notes: result.notes },
      ]);
      // Keep `questions` so the panel stays on its "已融入 N 处 + 重新提问" done
      // state (clearing it would unmount the panel and hide that a round ran).
    } catch (err) {
      setIntegrateError(err instanceof Error ? err.message : "融入失败");
    } finally {
      setIntegrating(false);
    }
  }

  function handleAdopt(improved: string) {
    setText(improved);
    // The draft becomes the new source → clear everything; back to the editor.
    setResult(null);
    setDocReviewResult(null);
    setDocReviewError(null);
    resetWorktop();
    resetDeepDive();
    setActiveTab("source");
  }

  // ── Derived ─────────────────────────────────────────────────────────────────

  const writingDims: Dimension[] = result?.dimensions.filter((d) => d.layer === "writing") ?? [];
  const substanceDims: Dimension[] = result?.dimensions.filter((d) => d.layer === "substance") ?? [];

  const writingApplied = worklog.filter((e) => e.source === "writing").reduce((n, e) => n + e.applied.length, 0);
  const substanceApplied = worklog.filter((e) => e.source === "substance").reduce((n, e) => n + e.applied.length, 0);
  const hasWritingWork = worklog.some((e) => e.source === "writing");

  const steps: { label: string; state: StepState }[] = [
    { label: "诊断", state: result ? "done" : "active" },
    {
      label: "改写作",
      state: !result ? "todo" : hasWritingWork ? "done" : "active",
    },
    {
      label: "深挖实质",
      state: !result ? "todo" : substanceApplied > 0 ? "done" : "active",
    },
    {
      label: "文档审阅",
      state: docReviewResult ? "done" : result ? "active" : "todo",
    },
  ];

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
            打磨论文{" "}
            <span className="text-ink/40 font-normal">Polish</span>
          </h1>
          <p className="text-sm text-ink/55 leading-6">
            贴入或上传论文 → 一次诊断，分清「写作层（AI 可代改）」与「实质层（需你补料）」，再分别动手。
          </p>
        </div>
      </div>

      {/* ── Tabs (full-width, not split-screen) ── */}
      <div className="flex items-center gap-1 border-b border-ink/10">
        <button
          onClick={() => setActiveTab("source")}
          className="relative px-4 py-2.5 text-sm font-semibold transition-colors"
          style={{ color: activeTab === "source" ? WRITING_DARK : "rgba(20,33,61,0.45)" }}
        >
          原文 · {charCount} 字
          {activeTab === "source" && (
            <span className="absolute left-0 right-0 -bottom-px h-0.5" style={{ background: WRITING }} />
          )}
        </button>
        <button
          onClick={() => {
            if (result || hasEnough) setActiveTab("polish");
          }}
          disabled={!result && !hasEnough}
          className="relative px-4 py-2.5 text-sm font-semibold transition-colors"
          style={{
            color:
              activeTab === "polish"
                ? WRITING_DARK
                : result || hasEnough
                  ? "rgba(20,33,61,0.45)"
                  : "rgba(20,33,61,0.25)",
            cursor: result || hasEnough ? "pointer" : "not-allowed",
          }}
        >
          打磨{result ? "" : "（先诊断）"}
          {activeTab === "polish" && (
            <span className="absolute left-0 right-0 -bottom-px h-0.5" style={{ background: WRITING }} />
          )}
        </button>
      </div>

      {/* ── 原文 tab: the editor ── */}
      {activeTab === "source" && (
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

          {/* ── Primary action: diagnose ── */}
          <button
            onClick={handleEvaluate}
            disabled={!canEvaluate}
            className="flex w-full items-center justify-center gap-2 rounded-[16px] py-3.5 text-sm font-semibold text-white transition-all"
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
                诊断中…（约 10–30 秒）
              </>
            ) : (
              <>
                <Sparkles size={16} />
                {result ? "重新诊断" : "开始打磨 · 诊断"}
              </>
            )}
          </button>
          <p className="text-[11px] text-ink/40 leading-5 text-center">
            诊断后自动进入「打磨」：逐维度评分 + 写作层/实质层，改写作 / 深挖 / 审阅一条龙，最后一次采纳回到这里。
          </p>

          {/* Eval error */}
          {evalError && (
            <p className="rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-xs text-red-600">
              {evalError}
            </p>
          )}
        </div>
      )}

      {/* ── 打磨 tab: diagnose → improve → deep-dive → review → adopt ── */}
      {activeTab === "polish" && (
        <div className="rounded-[28px] border border-ink/10 bg-white/85 shadow-panel p-6 space-y-6">
          {/* Progress rail */}
          <ProgressRail steps={steps} />

          <div className="border-t border-ink/8" />

          {/* Empty state */}
          {!result && (
            <div className="flex min-h-[280px] flex-col items-center justify-center gap-4">
              <p className="text-center text-sm text-ink/40 px-8 leading-7">
                还没有诊断结果。
                <br />
                到「原文」标签贴入论文并诊断，结果会显示在这里。
              </p>
              <button
                onClick={() => setActiveTab("source")}
                className="rounded-[14px] px-5 py-2.5 text-sm font-semibold transition-all"
                style={{ background: "rgba(95,179,163,0.12)", color: WRITING_DARK, border: "1px solid rgba(95,179,163,0.35)" }}
              >
                ← 去「原文」诊断
              </button>
            </div>
          )}

          {/* Diagnosis flow */}
          {result && (
            <div className="space-y-6">
              {/* Overall block */}
              <div className="space-y-4">
                <span
                  className="inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold tracking-wide"
                  style={{
                    background: "rgba(95,179,163,0.12)",
                    color: "#3f8a7d",
                    border: "1px solid rgba(95,179,163,0.25)",
                  }}
                >
                  {result.overall.band}
                </span>
                <p className="text-sm leading-7 text-ink/80">{result.overall.summary}</p>
                <div
                  className="rounded-xl p-4 space-y-1"
                  style={{
                    background: "rgba(95,179,163,0.08)",
                    border: "1px solid rgba(95,179,163,0.20)",
                  }}
                >
                  <p className="text-[10px] font-semibold uppercase tracking-[0.28em]" style={{ color: WRITING }}>
                    最值得先改的一件事
                  </p>
                  <p className="text-sm leading-6 text-ink/80">{result.overall.top_fix}</p>
                </div>
              </div>

              <div className="border-t border-ink/8" />

              {/* ── 写作层 ── */}
              <div className="space-y-4">
                <LayerHeader
                  title="写作层"
                  badge="AI 可代改"
                  accent={WRITING_DARK}
                  subtitle="论点表达、论证组织、结构连贯、行文——这些 AI 能直接帮你改。"
                />
                {writingDims.length === 0 ? (
                  <p className="text-xs text-ink/40">（本篇未单列写作层维度）</p>
                ) : (
                  <div className="space-y-3">
                    {writingDims.map((dim, i) => (
                      <DimensionCard key={i} {...dim} accent={WRITING} />
                    ))}
                  </div>
                )}

                {/* 一键改写作 CTA — edits the shared worktop */}
                <button
                  onClick={handleImprove}
                  disabled={!canImprove}
                  className="flex w-full items-center justify-center gap-2 rounded-[16px] py-3 text-sm font-semibold transition-all"
                  style={{
                    background: canImprove ? "rgba(95,179,163,0.12)" : "rgba(20,33,61,0.08)",
                    color: canImprove ? WRITING_DARK : "rgba(20,33,61,0.30)",
                    border: canImprove
                      ? "1px solid rgba(95,179,163,0.35)"
                      : "1px solid rgba(20,33,61,0.10)",
                    cursor: canImprove ? "pointer" : "not-allowed",
                  }}
                >
                  {improving ? (
                    <>
                      <Loader2 size={15} className="animate-spin" />
                      改写作中…（读全文、出编辑，约 20–40 秒）
                    </>
                  ) : (
                    <>
                      <Sparkles size={15} />
                      {hasWritingWork ? "再改一轮（在工作稿上）" : "一键改写作"}
                    </>
                  )}
                </button>
                <p className="text-[11px] text-ink/40 leading-5 text-center -mt-1">
                  {hasWritingWork
                    ? `已写入工作稿 ${writingApplied} 处 · 改动汇总见下方「改进工作稿」。`
                    : "AI 按写作问题改写，结果汇入下方「改进工作稿」；只改写作，不编造内容。"}
                </p>

                {improveError && (
                  <p className="rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-xs text-red-600">
                    {improveError}
                  </p>
                )}
              </div>

              <div className="border-t border-ink/8" />

              {/* ── 实质层 ── */}
              <div className="space-y-4">
                <LayerHeader
                  title="实质层"
                  badge="需你补料"
                  accent={SUBSTANCE_DARK}
                  subtitle="严谨性、原创与贡献——AI 不能替你编造数据、证据或新观点，只能引导你补充真材料。"
                />
                {substanceDims.length === 0 ? (
                  <p className="text-xs text-ink/40">（本篇未单列实质层维度）</p>
                ) : (
                  <div className="space-y-3">
                    {substanceDims.map((dim, i) => (
                      <DimensionCard key={i} {...dim} accent={SUBSTANCE} />
                    ))}
                  </div>
                )}

                {/* 深挖实质: probe → answer → integrate */}
                {!questions ? (
                  <>
                    <button
                      onClick={handleProbe}
                      disabled={busy || !hasEnough}
                      className="flex w-full items-center justify-center gap-2 rounded-[16px] py-3 text-sm font-semibold transition-all"
                      style={{
                        background: !busy && hasEnough ? "rgba(176,125,46,0.10)" : "rgba(20,33,61,0.08)",
                        color: !busy && hasEnough ? SUBSTANCE_DARK : "rgba(20,33,61,0.30)",
                        border:
                          !busy && hasEnough
                            ? "1px solid rgba(176,125,46,0.38)"
                            : "1px solid rgba(20,33,61,0.10)",
                        cursor: !busy && hasEnough ? "pointer" : "not-allowed",
                      }}
                    >
                      {probing ? (
                        <>
                          <Loader2 size={15} className="animate-spin" />
                          出题中…（就薄弱处提问，约 15–30 秒）
                        </>
                      ) : (
                        <>
                          <Compass size={15} />
                          深挖实质 · 让 AI 向我提问
                        </>
                      )}
                    </button>
                    <p className="text-[11px] text-ink/40 leading-5 text-center -mt-1">
                      AI 就薄弱处向你提 3–5 个问题，你补真实材料后再融入论文——绝不替你编造。
                    </p>
                  </>
                ) : (
                  <DeepDivePanel
                    key={questions.map((q) => q.question).join("|")}
                    questions={questions}
                    integrating={integrating}
                    integrateError={integrateError}
                    integratedCount={substanceApplied}
                    onIntegrate={handleIntegrate}
                    onReprobe={handleProbe}
                  />
                )}

                {probeError && (
                  <p className="rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-xs text-red-600">
                    {probeError}
                  </p>
                )}
              </div>

              {/* ── 改进工作稿（写作 + 实质 汇总，唯一导出/采纳处）── */}
              {draft !== null && (
                <>
                  <div className="border-t border-ink/8" />
                  <WorktopPanel
                    draft={draft}
                    worklog={worklog}
                    busy={busy}
                    onAdopt={handleAdopt}
                    onReset={resetWorktop}
                  />
                </>
              )}

              <div className="border-t border-ink/8" />

              {/* ── 文档审阅 ── */}
              <div className="space-y-4">
                <LayerHeader
                  title="文档审阅"
                  badge="可选"
                  accent={WRITING_DARK}
                  subtitle="脚注/引用重复、术语一致性、重复冗余、结构格式——生成可在自己编辑器中执行的修改清单，不重写文件。"
                />
                <button
                  onClick={handleDocReview}
                  disabled={!canDocReview}
                  className="flex w-full items-center justify-center gap-2 rounded-[16px] py-3 text-sm font-semibold transition-all"
                  style={{
                    background: "transparent",
                    color: canDocReview ? WRITING_DARK : "rgba(20,33,61,0.28)",
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
                    <>
                      <FileSearch size={15} />
                      {docReviewResult ? "重新审阅" : "运行文档审阅"}
                    </>
                  )}
                </button>

                {docReviewError && (
                  <p className="rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-xs text-red-600">
                    {docReviewError}
                  </p>
                )}

                {docReviewResult && <DocReviewPanel review={docReviewResult} />}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
