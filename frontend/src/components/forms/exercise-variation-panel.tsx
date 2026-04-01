"use client";

import { useState } from "react";
import Link from "next/link";
import { portalApi } from "@/lib/api/portal";
import type { AIFeedbackResponse, ExerciseVariation, PinnedExercise, VariationType } from "@/lib/types/portal";
import { AIFeedbackDisplay } from "@/components/forms/ai-feedback-display";
import { LessonMarkdown } from "@/components/learning/lesson-markdown";

interface Props {
  variation: ExerciseVariation;
  exerciseId: number;
  onDiscard: () => void;
  onPinned: (pinned: PinnedExercise) => void;
}

const VARIATION_LABELS: Record<VariationType, string> = {
  scenario: "New Scenario",
  concept: "Concept Shift",
  harder: "Harder Challenge",
};

const VARIATION_COLORS: Record<VariationType, string> = {
  scenario: "bg-[#e7d8c9] text-[#14213d]",
  concept: "bg-[#d9f0e1] text-[#264653]",
  harder: "bg-[#f77f00]/10 text-[#f77f00]",
};

export function ExerciseVariationPanel({ variation, exerciseId, onDiscard, onPinned }: Props) {
  const [code, setCode] = useState(variation.starter_code);
  const [feedback, setFeedback] = useState<AIFeedbackResponse | null>(null);
  const [feedbackLoading, setFeedbackLoading] = useState(false);
  const [feedbackError, setFeedbackError] = useState<string | null>(null);
  const [pinning, setPinning] = useState(false);
  const [pinError, setPinError] = useState<string | null>(null);
  const [pinned, setPinned] = useState<PinnedExercise | null>(null);

  async function handleGetFeedback() {
    setFeedbackLoading(true);
    setFeedbackError(null);
    setFeedback(null);
    try {
      const result = await portalApi.submitForAIFeedback(exerciseId, code, variation.solution_code);
      setFeedback(result);
    } catch (err) {
      setFeedbackError(err instanceof Error ? err.message : "AI feedback unavailable");
    } finally {
      setFeedbackLoading(false);
    }
  }

  async function handlePin() {
    setPinning(true);
    setPinError(null);
    try {
      const result = await portalApi.pinVariation(exerciseId, variation);
      setPinned(result);
      onPinned(result);
    } catch (err) {
      setPinError(err instanceof Error ? err.message : "Pin failed");
    } finally {
      setPinning(false);
    }
  }

  return (
    <div
      className="rounded-xl border border-[#e7d8c9] bg-[#f8f3e8]/60 mt-6"
      style={{ borderLeft: "4px solid #f77f00" }}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-4 p-5 pb-3">
        <div className="flex flex-col gap-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span
              className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold ${VARIATION_COLORS[variation.variation_type]}`}
            >
              {VARIATION_LABELS[variation.variation_type]}
            </span>
            <span className="text-xs text-[#14213d]/40">Generated variation</span>
          </div>
          <h2 className="text-base font-bold text-[#14213d] leading-snug">{variation.title}</h2>
        </div>
      </div>

      {/* Prompt */}
      <div className="px-5 pb-3">
        <LessonMarkdown content={variation.prompt_md} />
      </div>

      {/* Code editor */}
      <div className="px-5 pb-3">
        <label className="block text-xs font-semibold text-[#14213d]/50 uppercase tracking-wide mb-1.5">
          Your Code
        </label>
        <textarea
          className="w-full rounded-lg border border-[#e7d8c9] bg-[#0f172a] text-green-300 font-mono text-sm p-4 min-h-[200px] resize-y focus:outline-none focus:ring-2 focus:ring-[#f77f00]/50"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          spellCheck={false}
          aria-label="Code editor"
        />
      </div>

      {/* Get AI Feedback */}
      <div className="px-5 pb-3">
        <button
          onClick={handleGetFeedback}
          disabled={feedbackLoading || !code.trim()}
          className="rounded-lg bg-[#264653] text-white text-sm font-semibold px-4 py-2 hover:bg-[#264653]/80 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {feedbackLoading ? "Getting feedback…" : "Get AI Feedback"}
        </button>

        <AIFeedbackDisplay
          feedback={feedback}
          isLoading={feedbackLoading}
          error={feedbackError}
        />
      </div>

      {/* Pin success */}
      {pinned && (
        <div className="mx-5 mb-4 rounded-lg bg-[#d9f0e1] border border-[#264653]/20 px-4 py-3 flex items-center gap-3">
          <span className="text-sm font-semibold text-[#264653]">Pinned to library!</span>
          <Link
            href={`/practice/python/${pinned.id}`}
            className="text-sm text-[#f77f00] font-semibold underline underline-offset-2 hover:text-[#f77f00]/80"
          >
            Open: {pinned.title}
          </Link>
        </div>
      )}

      {/* Action buttons */}
      <div className="flex items-center gap-3 px-5 pb-5 pt-2 border-t border-[#e7d8c9] mt-2">
        {!pinned && (
          <button
            onClick={handlePin}
            disabled={pinning}
            className="rounded-lg bg-[#f77f00] text-white text-sm font-semibold px-5 py-2 hover:bg-[#f77f00]/85 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {pinning ? "Pinning…" : "Pin to Library"}
          </button>
        )}
        <button
          onClick={onDiscard}
          className="rounded-lg border border-[#e7d8c9] bg-transparent text-[#14213d]/70 text-sm font-medium px-4 py-2 hover:border-[#14213d]/30 hover:text-[#14213d] transition-colors"
        >
          Discard
        </button>
        {pinError && (
          <span className="text-xs text-red-600">{pinError}</span>
        )}
      </div>
    </div>
  );
}
