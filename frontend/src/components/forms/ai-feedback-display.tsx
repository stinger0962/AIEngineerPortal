"use client";

import { AIFeedbackResponse } from "@/lib/types/portal";

interface Props {
  feedback: AIFeedbackResponse | null;
  isLoading: boolean;
  error: string | null;
}

export function AIFeedbackDisplay({ feedback, isLoading, error }: Props) {
  if (isLoading) {
    return (
      <div className="rounded-xl border border-sand/50 bg-cream/50 p-6 mt-4">
        <div className="flex items-center gap-3">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-ember border-t-transparent" />
          <p className="text-ink/60 text-sm">AI is reviewing your code...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-6 mt-4">
        <p className="text-red-700 text-sm font-medium">AI Feedback Error</p>
        <p className="text-red-600 text-sm mt-1">{error}</p>
      </div>
    );
  }

  if (!feedback) return null;

  const scoreColor =
    feedback.score >= 85
      ? "text-green-700 bg-mint"
      : feedback.score >= 70
        ? "text-amber-700 bg-amber-50"
        : "text-red-700 bg-red-50";

  return (
    <div className="rounded-xl border border-sand/50 bg-cream/30 p-6 mt-4 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold tracking-wide uppercase text-ink/50">
          AI Feedback
          {feedback.cached && (
            <span className="ml-2 text-xs text-ink/30">(cached)</span>
          )}
        </h3>
        <span className={`px-3 py-1 rounded-full text-sm font-bold ${scoreColor}`}>
          {feedback.score}/100
        </span>
      </div>

      {feedback.strengths.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-green-700 mb-1">Strengths</h4>
          <ul className="list-disc list-inside text-sm text-ink/70 space-y-1">
            {feedback.strengths.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </div>
      )}

      {feedback.issues.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-red-700 mb-1">Issues</h4>
          <ul className="list-disc list-inside text-sm text-ink/70 space-y-1">
            {feedback.issues.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </div>
      )}

      {feedback.suggestions.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-amber-700 mb-1">Suggestions</h4>
          <ul className="list-disc list-inside text-sm text-ink/70 space-y-1">
            {feedback.suggestions.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </div>
      )}

      {feedback.example_fixes && (
        <div>
          <h4 className="text-sm font-medium text-pine mb-1">Example Fixes</h4>
          <pre className="rounded-lg bg-[#0f172a] p-4 text-sm text-green-300 font-mono whitespace-pre-wrap overflow-x-auto">
            {feedback.example_fixes}
          </pre>
        </div>
      )}

      {feedback.should_retry && (
        <p className="text-sm text-ember font-medium">
          Keep going — revise your code and try again!
        </p>
      )}

      {!feedback.should_retry && (
        <p className="text-sm text-green-700 font-medium">
          Great work — this solution looks solid!
        </p>
      )}

      {feedback.latency_ms && (
        <p className="text-xs text-ink/30">
          Graded in {(feedback.latency_ms / 1000).toFixed(1)}s
          {feedback.input_tokens && ` · ${feedback.input_tokens + (feedback.output_tokens || 0)} tokens`}
        </p>
      )}
    </div>
  );
}
