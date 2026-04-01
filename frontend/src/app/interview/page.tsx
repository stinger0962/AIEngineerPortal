import Link from "next/link";
import { Target, TrendingUp, AlertTriangle, BookOpen } from "lucide-react";

import { InterviewQuestionBoard } from "@/components/interview/interview-question-board";
import { Panel } from "@/components/ui/panel";
import { portalApi } from "@/lib/api/portal";

function scoreColor(score: number): string {
  if (score >= 75) return "text-pine";
  if (score >= 50) return "text-ember";
  return "text-[#dc2626]";
}

function scoreBg(score: number): string {
  if (score >= 75) return "bg-mint";
  if (score >= 50) return "bg-ember/10";
  return "bg-red-50";
}

export default async function InterviewPage() {
  const [questions, roadmap, readiness, skillGaps] = await Promise.all([
    portalApi.getInterviewQuestions(),
    portalApi.getInterviewRoadmap(),
    portalApi.getPortfolioReadiness(),
    portalApi.getInterviewSkillGaps(),
  ]);

  return (
    <div className="space-y-8">
      {/* Hero */}
      <div className="relative overflow-hidden rounded-[28px] bg-gradient-to-br from-ink via-ink/95 to-pine p-8 text-cream">
        <div className="absolute top-0 right-0 w-64 h-64 bg-ember/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/4" />
        <div className="relative">
          <span className="text-xs font-semibold uppercase tracking-[0.28em] text-ember">Interview Prep</span>
          <h1 className="mt-2 font-display text-3xl lg:text-4xl leading-tight">Turn progress into interview readiness.</h1>
          <p className="mt-3 text-cream/60 max-w-2xl text-[15px] leading-7">
            AI-powered coaching on {questions.length} questions. Practice answers, get real-time feedback, and track your readiness score.
          </p>

          {/* Score bar */}
          <div className="mt-6 flex flex-wrap gap-6">
            <div className={`rounded-2xl ${scoreBg(readiness.overall_score)} px-6 py-4 text-center`}>
              <p className={`text-4xl font-bold ${scoreColor(readiness.overall_score)}`}>{readiness.overall_score}</p>
              <p className="text-xs uppercase tracking-wide text-ink/50 mt-1">Readiness</p>
            </div>
            <div className="rounded-2xl bg-white/10 px-6 py-4 text-center">
              <p className="text-4xl font-bold text-mint">{readiness.strongest_signals.length}</p>
              <p className="text-xs uppercase tracking-wide text-cream/50 mt-1">Strengths</p>
            </div>
            <div className="rounded-2xl bg-white/10 px-6 py-4 text-center">
              <p className="text-4xl font-bold text-ember">{readiness.gaps_to_close.length}</p>
              <p className="text-xs uppercase tracking-wide text-cream/50 mt-1">Gaps</p>
            </div>
            <div className="rounded-2xl bg-white/10 px-6 py-4 text-center">
              <p className="text-4xl font-bold text-cream">{questions.length}</p>
              <p className="text-xs uppercase tracking-wide text-cream/50 mt-1">Questions</p>
            </div>
          </div>
        </div>
      </div>

      {/* Two-column: coaching sidebar + questions */}
      <div className="grid gap-6 xl:grid-cols-[1fr_2fr]">
        {/* Left sidebar: roadmap + gaps */}
        <div className="space-y-6">
          {/* Weekly rhythm */}
          <Panel className="space-y-3">
            <div className="flex items-center gap-2">
              <Target size={16} className="text-ember" />
              <h2 className="text-xs font-semibold uppercase tracking-[0.28em] text-ember">This Week</h2>
            </div>
            {roadmap.weekly_plan.map((item, i) => (
              <div key={item} className="flex gap-3 text-sm text-ink/80">
                <span className="shrink-0 w-6 h-6 rounded-full bg-mint flex items-center justify-center text-xs font-bold text-pine">{i + 1}</span>
                <span className="leading-6">{item}</span>
              </div>
            ))}
          </Panel>

          {/* Focus areas */}
          <Panel className="space-y-3">
            <div className="flex items-center gap-2">
              <TrendingUp size={16} className="text-pine" />
              <h2 className="text-xs font-semibold uppercase tracking-[0.28em] text-pine">Focus Areas</h2>
            </div>
            {roadmap.focus_areas.map((item) => (
              <p key={item} className="text-sm text-ink/70 leading-6 pl-1 border-l-2 border-pine/30 ml-1">{item}</p>
            ))}
          </Panel>

          {/* Skill gaps */}
          {skillGaps.length > 0 && (
            <Panel className="space-y-3">
              <div className="flex items-center gap-2">
                <AlertTriangle size={16} className="text-ember" />
                <h2 className="text-xs font-semibold uppercase tracking-[0.28em] text-ember">Skill Gaps</h2>
              </div>
              {skillGaps.slice(0, 4).map((gap) => (
                <div key={`${gap.title}-${gap.action_path}`} className="space-y-1">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-semibold text-ink">{gap.title}</p>
                    <span className={`text-[10px] uppercase tracking-wide px-2 py-0.5 rounded-full ${gap.urgency === "high" ? "bg-ember/10 text-ember" : "bg-sand text-ink/50"}`}>
                      {gap.urgency}
                    </span>
                  </div>
                  <p className="text-xs text-ink/50">{gap.evidence}</p>
                  <Link href={gap.action_path} className="text-xs text-ember hover:text-ink underline underline-offset-2 transition-colors">
                    Study this →
                  </Link>
                </div>
              ))}
            </Panel>
          )}

          {/* Next best moves */}
          {readiness.next_best_moves?.length > 0 && (
            <Panel className="space-y-3">
              <div className="flex items-center gap-2">
                <BookOpen size={16} className="text-ink/50" />
                <h2 className="text-xs font-semibold uppercase tracking-[0.28em] text-ink/50">Next Moves</h2>
              </div>
              {readiness.next_best_moves.map((item) => (
                <p key={item} className="text-sm text-ink/70 leading-6">{item}</p>
              ))}
            </Panel>
          )}
        </div>

        {/* Right: Question board */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xs font-semibold uppercase tracking-[0.28em] text-ember">Questions ({questions.length})</h2>
          </div>
          <InterviewQuestionBoard initialQuestions={questions} />
        </div>
      </div>
    </div>
  );
}
