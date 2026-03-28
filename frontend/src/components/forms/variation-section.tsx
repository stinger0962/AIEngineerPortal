"use client";

import { useState } from "react";
import { portalApi } from "@/lib/api/portal";
import type { ExerciseVariation, PinnedExercise, VariationType } from "@/lib/types/portal";
import { ExerciseVariationPanel } from "@/components/forms/exercise-variation-panel";

interface Props {
  exerciseId: number;
}

const VARIATION_OPTIONS: { value: VariationType; label: string }[] = [
  { value: "scenario", label: "Same concept, different scenario" },
  { value: "concept", label: "Different concept" },
  { value: "harder", label: "Harder version" },
];

export function VariationSection({ exerciseId }: Props) {
  const [variation, setVariation] = useState<ExerciseVariation | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [variationType, setVariationType] = useState<VariationType>("scenario");
  const [pinnedSuccess, setPinnedSuccess] = useState<PinnedExercise | null>(null);

  async function handleGenerate() {
    setIsGenerating(true);
    setError(null);
    setVariation(null);
    setPinnedSuccess(null);
    try {
      const result = await portalApi.generateVariation(exerciseId, variationType);
      setVariation(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate variation");
    } finally {
      setIsGenerating(false);
    }
  }

  function handleDiscard() {
    setVariation(null);
    setError(null);
    setPinnedSuccess(null);
  }

  function handlePinned(pinned: PinnedExercise) {
    setPinnedSuccess(pinned);
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 flex-wrap">
        <select
          value={variationType}
          onChange={(e) => setVariationType(e.target.value as VariationType)}
          disabled={isGenerating}
          className="rounded-lg border border-ink/20 bg-white px-3 py-2 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-ember/50 disabled:opacity-50"
        >
          {VARIATION_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <button
          onClick={handleGenerate}
          disabled={isGenerating}
          className="rounded-lg bg-ember text-white text-sm font-semibold px-5 py-2 hover:bg-ember/85 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isGenerating ? "Generating…" : "Generate Variation"}
        </button>
      </div>

      {isGenerating && (
        <div className="flex items-center gap-3 text-sm text-ink/70 py-2">
          <svg
            className="h-4 w-4 animate-spin text-ember"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
            />
          </svg>
          Generating a new variation…
        </div>
      )}

      {error && (
        <p className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>
      )}

      {variation && (
        <ExerciseVariationPanel
          variation={variation}
          exerciseId={exerciseId}
          onDiscard={handleDiscard}
          onPinned={handlePinned}
        />
      )}
    </div>
  );
}
