"use client";

import { startTransition, useState } from "react";

import { LessonMarkdown } from "@/components/learning/lesson-markdown";
import { portalApi } from "@/lib/api/portal";
import type { InterviewQuestion } from "@/lib/types/portal";

type InterviewQuestionBoardProps = {
  initialQuestions: InterviewQuestion[];
};

export function InterviewQuestionBoard({ initialQuestions }: InterviewQuestionBoardProps) {
  const [questions, setQuestions] = useState(initialQuestions);
  const [activeQuestionId, setActiveQuestionId] = useState<number | null>(null);

  async function handlePractice(questionId: number, confidenceScore: number) {
    setActiveQuestionId(questionId);
    try {
      const result = await portalApi.practiceInterviewQuestion(questionId, confidenceScore, `Confidence ${confidenceScore}/5`);
      startTransition(() =>
        setQuestions((current) =>
          current.map((question) =>
            question.id === questionId
              ? {
                  ...question,
                  practice_count: result.practice_count,
                  last_practiced_at: result.last_practiced_at,
                  average_confidence: result.average_confidence,
                }
              : question,
          ),
        ),
      );
    } finally {
      setActiveQuestionId(null);
    }
  }

  return (
    <div className="space-y-4">
      {questions.map((question) => (
        <div key={question.id} className="rounded-[24px] bg-cream p-5">
          <div className="flex flex-wrap items-center gap-2 text-xs uppercase tracking-[0.24em] text-ink/50">
            <span>{question.category}</span>
            <span>{question.difficulty}</span>
            <span>Practiced {question.practice_count}x</span>
            {question.average_confidence ? <span>Confidence {question.average_confidence}/5</span> : null}
          </div>
          <h3 className="mt-2 text-lg font-semibold text-ink">{question.question_text}</h3>
          <div className="mt-4 rounded-2xl bg-white/75 p-4">
            <LessonMarkdown content={question.answer_outline_md} />
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {question.tags_json.map((tag) => (
              <span key={tag} className="rounded-full border border-ink/10 bg-white px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-ink/60">
                {tag}
              </span>
            ))}
          </div>
          {question.last_practiced_at ? (
            <p className="mt-2 text-xs text-ink/55">Last practiced {new Date(question.last_practiced_at).toLocaleString()}</p>
          ) : null}
          <div className="mt-4 flex flex-wrap gap-2">
            {[2, 3, 4, 5].map((confidence) => (
              <button
                key={confidence}
                type="button"
                onClick={() => handlePractice(question.id, confidence)}
                disabled={activeQuestionId === question.id}
                className="inline-flex rounded-full border border-ink/10 px-4 py-2 text-sm font-semibold disabled:opacity-50"
              >
                {activeQuestionId === question.id ? "Saving..." : `Log rep ${confidence}/5`}
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
