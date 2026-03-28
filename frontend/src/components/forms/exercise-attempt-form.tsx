"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { portalApi } from "@/lib/api/portal";
import { AIFeedbackResponse } from "@/lib/types/portal";
import { AIFeedbackDisplay } from "./ai-feedback-display";

interface Props {
  exerciseId: number;
  starterCode: string;
}

export function ExerciseAttemptForm({ exerciseId, starterCode }: Props) {
  const router = useRouter();
  const [code, setCode] = useState(starterCode);
  const [notes, setNotes] = useState("");
  const [feedback, setFeedback] = useState<AIFeedbackResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState("");

  async function onSubmitAI() {
    setIsLoading(true);
    setError(null);
    setFeedback(null);
    setStatus("");

    try {
      const result = await portalApi.submitForAIFeedback(exerciseId, code);
      setFeedback(result);
      if (!result.should_retry) {
        setStatus(`Completed with score ${result.score}/100`);
      }
    } catch (err: any) {
      setError(err.message || "AI feedback failed");
      // Fallback to basic submission
      try {
        const basic = await portalApi.submitAttempt(exerciseId, code, notes);
        setStatus(`Fallback score: ${basic.score}/100 (AI unavailable)`);
      } catch {
        setStatus("Submission failed");
      }
    } finally {
      setIsLoading(false);
      router.refresh();
    }
  }

  async function onSubmitBasic() {
    setIsLoading(true);
    setStatus("");
    try {
      const result = await portalApi.submitAttempt(exerciseId, code, notes);
      setStatus(`Score: ${result.score}/100`);
    } catch {
      setStatus("Submit failed");
    } finally {
      setIsLoading(false);
      router.refresh();
    }
  }

  return (
    <div className="space-y-4">
      <textarea
        value={code}
        onChange={(e) => setCode(e.target.value)}
        rows={14}
        className="w-full rounded-lg border border-sand bg-[#fffdf7] p-4 font-mono text-sm"
        placeholder="Write your solution here..."
      />
      <textarea
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        rows={2}
        className="w-full rounded-lg border border-sand bg-[#fffdf7] p-3 text-sm"
        placeholder="Notes or reflections (optional)..."
      />
      <div className="flex gap-3">
        <button
          onClick={onSubmitAI}
          disabled={isLoading || !code.trim()}
          className="rounded-lg bg-ember px-5 py-2 text-sm font-semibold text-white hover:bg-ember/90 disabled:opacity-40"
        >
          {isLoading ? "Grading..." : "Get AI Feedback"}
        </button>
        <button
          onClick={onSubmitBasic}
          disabled={isLoading || !code.trim()}
          className="rounded-lg bg-pine px-5 py-2 text-sm font-semibold text-white hover:bg-pine/90 disabled:opacity-40"
        >
          Quick Submit
        </button>
      </div>

      {status && (
        <p className="text-sm text-ink/60">{status}</p>
      )}

      <AIFeedbackDisplay
        feedback={feedback}
        isLoading={isLoading}
        error={error}
      />

      {feedback?.should_retry && (
        <div className="rounded-lg border border-ember/30 bg-ember/5 p-4">
          <p className="text-sm text-ink/70">
            Your code is still in the editor — revise it based on the feedback above and submit again.
          </p>
        </div>
      )}
    </div>
  );
}
