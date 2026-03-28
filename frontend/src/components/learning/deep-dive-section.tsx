"use client";

import { useEffect, useState } from "react";
import { portalApi } from "@/lib/api/portal";
import type { DeepDiveEntry } from "@/lib/types/portal";
import { LessonMarkdown } from "@/components/learning/lesson-markdown";

interface Props {
  lessonId: number;
}

function Spinner() {
  return (
    <span
      aria-hidden="true"
      className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-[#264653] border-t-transparent align-middle"
    />
  );
}

function ConceptChips({ concepts }: { concepts: string[] }) {
  if (!concepts.length) return null;
  return (
    <div className="mt-3 flex flex-wrap gap-2">
      {concepts.map((concept) => (
        <span
          key={concept}
          className="rounded-full bg-[#d9f0e1] px-2.5 py-0.5 text-xs font-medium text-[#264653]"
        >
          {concept}
        </span>
      ))}
    </div>
  );
}

function QAEntry({ entry, defaultOpen = false }: { entry: DeepDiveEntry; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="rounded-xl border border-[#e7d8c9] overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-start justify-between gap-3 px-4 py-3 text-left hover:bg-[#e7d8c9]/30 transition-colors"
      >
        <span className="text-sm font-semibold text-[#14213d] leading-snug">{entry.question}</span>
        <span className="mt-0.5 shrink-0 text-[#264653] text-base leading-none">
          {open ? "−" : "+"}
        </span>
      </button>
      {open && (
        <div className="border-t border-[#e7d8c9] px-4 py-4 bg-[#f8f3e8]/50">
          <LessonMarkdown content={entry.answer_md} />
          <ConceptChips concepts={entry.related_concepts} />
        </div>
      )}
    </div>
  );
}

export function DeepDiveSection({ lessonId }: Props) {
  const [question, setQuestion] = useState("");
  const [entries, setEntries] = useState<DeepDiveEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [historyLoading, setHistoryLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setHistoryLoading(true);
    portalApi
      .getDeepDives(lessonId)
      .then((history) => {
        if (!cancelled) setEntries(history);
      })
      .catch(() => {
        // non-fatal — history stays empty
      })
      .finally(() => {
        if (!cancelled) setHistoryLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [lessonId]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || loading) return;

    setLoading(true);
    setError(null);

    try {
      const entry = await portalApi.askDeepDive(lessonId, trimmed);
      setEntries((prev) => [entry, ...prev]);
      setQuestion("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Deep dive failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      className="rounded-xl border border-[#e7d8c9] bg-[#e7d8c9]/20 mt-6"
      style={{ borderLeft: "4px solid #264653" }}
    >
      {/* Header */}
      <div className="px-5 pt-5 pb-3">
        <div className="text-xs uppercase tracking-[0.2em] text-[#264653] font-semibold mb-1">
          Lesson Deep Dive
        </div>
        <p className="text-sm text-[#14213d]/70">
          Ask a follow-up question about this lesson and get an AI-powered explanation.
        </p>
      </div>

      {/* Question input */}
      <form onSubmit={handleSubmit} className="px-5 pb-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask about this lesson..."
            disabled={loading}
            className="flex-1 rounded-lg border border-[#e7d8c9] bg-white px-3 py-2 text-sm text-[#14213d] placeholder-[#14213d]/40 focus:outline-none focus:ring-2 focus:ring-[#264653]/40 disabled:opacity-60"
          />
          <button
            type="submit"
            disabled={loading || !question.trim()}
            className="rounded-lg bg-[#f77f00] px-4 py-2 text-sm font-semibold text-white hover:bg-[#f77f00]/85 disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
          >
            Ask
          </button>
        </div>

        {/* Loading state */}
        {loading && (
          <div className="mt-3 flex items-center gap-2 text-sm text-[#264653]">
            <Spinner />
            <span>Thinking about your question...</span>
          </div>
        )}

        {/* Error state */}
        {error && !loading && (
          <p className="mt-2 text-sm text-red-600">{error}</p>
        )}
      </form>

      {/* Q&A history */}
      <div className="px-5 pb-5">
        {historyLoading ? (
          <div className="flex items-center gap-2 text-sm text-[#264653]/60 py-2">
            <Spinner />
            <span>Loading previous questions...</span>
          </div>
        ) : entries.length > 0 ? (
          <div className="space-y-2">
            <div className="text-xs font-semibold uppercase tracking-[0.18em] text-[#14213d]/50 mb-3">
              {entries.length} {entries.length === 1 ? "question" : "questions"}
            </div>
            {entries.map((entry, index) => (
              <QAEntry
                key={entry.id}
                entry={entry}
                defaultOpen={index === 0}
              />
            ))}
          </div>
        ) : (
          <p className="text-sm text-[#14213d]/45 py-1">
            No questions yet — ask something to get started.
          </p>
        )}
      </div>
    </div>
  );
}
