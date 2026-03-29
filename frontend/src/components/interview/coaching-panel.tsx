"use client";

import { useEffect, useState } from "react";

import { LessonMarkdown } from "@/components/learning/lesson-markdown";
import { portalApi } from "@/lib/api/portal";
import type { CoachingResult } from "@/lib/types/portal";

type InterviewCoachingPanelProps = {
  questionId: number;
  questionText: string;
  category: string;
};

function scoreColor(score: number): string {
  if (score >= 85) return "text-green-700";
  if (score >= 70) return "text-yellow-600";
  if (score >= 50) return "text-orange-500";
  return "text-red-600";
}

function scoreBg(score: number): string {
  if (score >= 85) return "bg-green-50 border-green-200";
  if (score >= 70) return "bg-yellow-50 border-yellow-200";
  if (score >= 50) return "bg-orange-50 border-orange-200";
  return "bg-red-50 border-red-200";
}

function formatDate(dateStr: string): string {
  try {
    return new Date(dateStr).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return dateStr;
  }
}

export function InterviewCoachingPanel({ questionId, questionText, category }: InterviewCoachingPanelProps) {
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<CoachingResult | null>(null);
  const [history, setHistory] = useState<CoachingResult[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [expandedHistoryId, setExpandedHistoryId] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    setHistoryLoading(true);
    portalApi.getCoachingHistory(questionId).then((data) => {
      if (!cancelled) {
        setHistory(data);
        setHistoryLoading(false);
      }
    }).catch(() => {
      if (!cancelled) setHistoryLoading(false);
    });
    return () => { cancelled = true; };
  }, [questionId]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!answer.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const coaching = await portalApi.submitForCoaching(questionId, answer.trim());
      setResult(coaching);
      setHistory((prev) => [coaching, ...prev]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Coaching failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  function handleTryAgain() {
    setResult(null);
  }

  return (
    <div className="mt-4 border-l-4 border-[#f77f00] pl-4 space-y-4">
      <p className="text-xs uppercase tracking-[0.2em] text-ink/50">AI Answer Coaching</p>

      {!result ? (
        <form onSubmit={handleSubmit} className="space-y-3">
          <textarea
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            placeholder="Write your answer here..."
            rows={7}
            className="w-full rounded-2xl border border-ink/10 bg-white p-4 text-sm text-ink placeholder:text-ink/40 focus:outline-none focus:ring-2 focus:ring-[#f77f00]/40 resize-none"
            disabled={loading}
          />
          {error ? (
            <p className="rounded-xl bg-red-50 px-4 py-2 text-sm text-red-700">{error}</p>
          ) : null}
          <button
            type="submit"
            disabled={loading || !answer.trim()}
            className="inline-flex rounded-full bg-[#f77f00] px-5 py-2 text-sm font-semibold text-white disabled:opacity-50 hover:bg-[#d96e00] transition-colors"
          >
            {loading ? "Coaching..." : "Get Coaching"}
          </button>
        </form>
      ) : (
        <div className="space-y-4">
          {/* Score header */}
          <div className={`rounded-2xl border p-5 ${scoreBg(result.overall_score)}`}>
            <div className="flex items-center justify-between gap-4 flex-wrap">
              <div>
                <p className="text-xs uppercase tracking-[0.2em] text-ink/50 mb-1">Overall Score</p>
                <p className={`text-5xl font-bold ${scoreColor(result.overall_score)}`}>
                  {result.overall_score}
                  <span className="text-2xl font-normal text-ink/40">/100</span>
                </p>
              </div>
              <span
                className={`rounded-full px-4 py-2 text-sm font-semibold ${
                  result.ready_for_interview
                    ? "bg-green-100 text-green-800"
                    : "bg-amber-100 text-amber-800"
                }`}
              >
                {result.ready_for_interview ? "Interview Ready" : "Needs Work"}
              </span>
            </div>
          </div>

          {/* Strengths */}
          {result.strengths.length > 0 ? (
            <div className="rounded-2xl bg-[#d9f0e1] p-4 space-y-2">
              <p className="text-xs uppercase tracking-[0.2em] text-ink/60 font-semibold">Strengths</p>
              <ul className="space-y-1.5">
                {result.strengths.map((s, i) => (
                  <li key={i} className="flex gap-2 text-sm text-ink/80">
                    <span className="mt-0.5 text-green-600 flex-shrink-0">&#10003;</span>
                    <span>{s}</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {/* Gaps */}
          {result.gaps.length > 0 ? (
            <div className="rounded-2xl bg-[#e7d8c9] p-4 space-y-2">
              <p className="text-xs uppercase tracking-[0.2em] text-ink/60 font-semibold">Gaps</p>
              <ul className="space-y-1.5">
                {result.gaps.map((g, i) => (
                  <li key={i} className="flex gap-2 text-sm text-ink/80">
                    <span className="mt-0.5 text-amber-600 flex-shrink-0">&#9651;</span>
                    <span>{g}</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {/* Improvements */}
          {result.improvements.length > 0 ? (
            <div className="rounded-2xl bg-white border border-ink/10 p-4 space-y-2">
              <p className="text-xs uppercase tracking-[0.2em] text-ink/60 font-semibold">How to improve</p>
              <ol className="space-y-1.5 pl-1">
                {result.improvements.map((imp, i) => (
                  <li key={i} className="flex gap-2.5 text-sm text-ink/80">
                    <span className="flex-shrink-0 font-semibold text-[#f77f00]">{i + 1}.</span>
                    <span>{imp}</span>
                  </li>
                ))}
              </ol>
            </div>
          ) : null}

          {/* Example answer */}
          {result.example_answer_section ? (
            <div className="rounded-2xl bg-white border border-ink/10 p-4 space-y-2">
              <p className="text-xs uppercase tracking-[0.2em] text-ink/60 font-semibold">Example answer</p>
              <LessonMarkdown content={result.example_answer_section} />
            </div>
          ) : null}

          <button
            type="button"
            onClick={handleTryAgain}
            className="inline-flex rounded-full border border-ink/15 px-5 py-2 text-sm font-semibold text-ink/70 hover:bg-ink/5 transition-colors"
          >
            Try Again
          </button>
        </div>
      )}

      {/* History */}
      {!historyLoading && history.length > 0 ? (
        <div className="space-y-2 pt-2 border-t border-ink/10">
          <p className="text-xs uppercase tracking-[0.2em] text-ink/40">Previous attempts</p>
          {history.map((attempt) => (
            <div key={attempt.id} className="rounded-2xl border border-ink/10 bg-white overflow-hidden">
              <button
                type="button"
                onClick={() => setExpandedHistoryId(expandedHistoryId === attempt.id ? null : attempt.id)}
                className="w-full flex items-center justify-between gap-4 px-4 py-3 text-left hover:bg-ink/3 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <span className={`text-lg font-bold ${scoreColor(attempt.overall_score)}`}>
                    {attempt.overall_score}
                  </span>
                  <span className="text-xs text-ink/50">
                    {attempt.ready_for_interview ? "Interview Ready" : "Needs Work"}
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  {attempt.created_at ? (
                    <span className="text-xs text-ink/40">{formatDate(attempt.created_at)}</span>
                  ) : null}
                  <span className="text-ink/30 text-xs">{expandedHistoryId === attempt.id ? "▲" : "▼"}</span>
                </div>
              </button>
              {expandedHistoryId === attempt.id ? (
                <div className="px-4 pb-4 space-y-3 border-t border-ink/10 pt-3">
                  {attempt.strengths.length > 0 ? (
                    <div>
                      <p className="text-xs font-semibold text-ink/50 mb-1">Strengths</p>
                      <ul className="space-y-1">
                        {attempt.strengths.map((s, i) => (
                          <li key={i} className="text-sm text-ink/70">&#10003; {s}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                  {attempt.gaps.length > 0 ? (
                    <div>
                      <p className="text-xs font-semibold text-ink/50 mb-1">Gaps</p>
                      <ul className="space-y-1">
                        {attempt.gaps.map((g, i) => (
                          <li key={i} className="text-sm text-ink/70">&#9651; {g}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                </div>
              ) : null}
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
