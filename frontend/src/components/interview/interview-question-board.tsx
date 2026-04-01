"use client";

import { startTransition, useState } from "react";
import { ChevronDown, ChevronUp, MessageSquare } from "lucide-react";

import { LessonMarkdown } from "@/components/learning/lesson-markdown";
import { InterviewCoachingPanel } from "@/components/interview/coaching-panel";
import { portalApi } from "@/lib/api/portal";
import type { InterviewQuestion } from "@/lib/types/portal";

type InterviewQuestionBoardProps = {
  initialQuestions: InterviewQuestion[];
};

const DIFFICULTY_COLORS: Record<string, string> = {
  beginner: "bg-mint text-pine",
  intermediate: "bg-sand text-ink",
  advanced: "bg-ember/15 text-ember",
};

const CATEGORY_COLORS: Record<string, string> = {
  python: "border-l-pine",
  backend: "border-l-[#0ea5e9]",
  "llm-systems": "border-l-ember",
  rag: "border-l-[#8b5cf6]",
  agents: "border-l-[#f43f5e]",
  evaluation: "border-l-[#10b981]",
  deployment: "border-l-[#6366f1]",
  "system-design": "border-l-[#0ea5e9]",
};

export function InterviewQuestionBoard({ initialQuestions }: InterviewQuestionBoardProps) {
  const [questions, setQuestions] = useState(initialQuestions);
  const [activeQuestionId, setActiveQuestionId] = useState<number | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [coachingId, setCoachingId] = useState<number | null>(null);
  const [filterCategory, setFilterCategory] = useState<string>("all");

  const categories = ["all", ...new Set(initialQuestions.map((q) => q.category))];
  const filtered = filterCategory === "all" ? questions : questions.filter((q) => q.category === filterCategory);

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
      {/* Category filter */}
      <div className="flex gap-2 flex-wrap">
        {categories.map((cat) => (
          <button
            key={cat}
            onClick={() => setFilterCategory(cat)}
            className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              filterCategory === cat
                ? "bg-ink text-cream"
                : "bg-ink/5 text-ink/60 hover:bg-ink/10"
            }`}
          >
            {cat === "all" ? "All" : cat.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
          </button>
        ))}
      </div>

      {/* Questions */}
      <div className="space-y-3">
        {filtered.map((question) => {
          const isExpanded = expandedId === question.id;
          const isCoaching = coachingId === question.id;

          return (
            <div
              key={question.id}
              className={`rounded-2xl border-l-4 ${CATEGORY_COLORS[question.category] || "border-l-ink/20"} bg-white/85 border border-ink/5 overflow-hidden transition-shadow ${isExpanded ? "shadow-lg" : "shadow-sm hover:shadow-md"}`}
            >
              {/* Collapsed header */}
              <button
                onClick={() => setExpandedId(isExpanded ? null : question.id)}
                className="w-full text-left px-5 py-4 flex items-start gap-3"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap mb-1">
                    <span className={`text-[10px] uppercase tracking-wide px-2 py-0.5 rounded-full font-semibold ${DIFFICULTY_COLORS[question.difficulty] || "bg-sand text-ink"}`}>
                      {question.difficulty}
                    </span>
                    <span className="text-[10px] text-ink/40 uppercase tracking-wide">
                      {question.category.replace(/-/g, " ")}
                    </span>
                    {question.practice_count > 0 && (
                      <span className="text-[10px] text-pine bg-mint/50 px-2 py-0.5 rounded-full">
                        {question.practice_count}x practiced
                      </span>
                    )}
                    {question.average_confidence ? (
                      <span className="text-[10px] text-ember bg-ember/10 px-2 py-0.5 rounded-full">
                        {question.average_confidence.toFixed(1)}/5
                      </span>
                    ) : null}
                  </div>
                  <h3 className="text-[15px] font-semibold text-ink leading-snug">{question.question_text}</h3>
                </div>
                <span className="shrink-0 mt-1 text-ink/30">
                  {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                </span>
              </button>

              {/* Expanded content */}
              {isExpanded && (
                <div className="px-5 pb-5 space-y-4 border-t border-ink/5 pt-4">
                  {/* Answer outline */}
                  <div className="rounded-xl bg-cream/70 p-4">
                    <p className="text-[10px] uppercase tracking-wide text-ink/40 font-semibold mb-2">Study Guide</p>
                    <LessonMarkdown content={question.answer_outline_md} />
                  </div>

                  {/* Tags */}
                  {question.tags_json?.length > 0 && (
                    <div className="flex gap-1.5 flex-wrap">
                      {question.tags_json.map((tag) => (
                        <span key={tag} className="text-[10px] text-ink/40 bg-ink/5 px-2 py-0.5 rounded-full">{tag}</span>
                      ))}
                    </div>
                  )}

                  {/* Actions row */}
                  <div className="flex items-center gap-3 flex-wrap">
                    <button
                      onClick={() => setCoachingId(isCoaching ? null : question.id)}
                      className="inline-flex items-center gap-2 rounded-full bg-ember px-4 py-2 text-sm font-semibold text-white hover:bg-[#e06f00] transition-colors"
                    >
                      <MessageSquare size={14} />
                      {isCoaching ? "Close Coaching" : "Practice with AI"}
                    </button>
                    <div className="flex gap-2">
                      {[2, 3, 4, 5].map((confidence) => (
                        <button
                          key={confidence}
                          onClick={() => handlePractice(question.id, confidence)}
                          disabled={activeQuestionId === question.id}
                          className="rounded-full border border-ink/10 px-3 py-1.5 text-xs font-medium text-ink/60 hover:bg-ink/5 disabled:opacity-50 transition-colors"
                        >
                          {activeQuestionId === question.id ? "..." : `${confidence}/5`}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* AI Coaching panel */}
                  {isCoaching && (
                    <InterviewCoachingPanel
                      questionId={question.id}
                      questionText={question.question_text}
                      category={question.category}
                    />
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
