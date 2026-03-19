import { Panel } from "@/components/ui/panel";
import { SectionHeading } from "@/components/ui/section-heading";
import { portalApi } from "@/lib/api/portal";

export default async function InterviewPage() {
  const [questions, roadmap, readiness] = await Promise.all([
    portalApi.getInterviewQuestions(),
    portalApi.getInterviewRoadmap(),
    portalApi.getPortfolioReadiness(),
  ]);

  return (
    <div className="space-y-6">
      <SectionHeading
        eyebrow="Interview Prep"
        title="Turn progress into interview readiness."
        description="Phase 3 starts by turning your live portal state into a personalized roadmap and a portfolio-readiness read."
      />
      <div className="grid gap-4 md:grid-cols-4">
        <Panel className="space-y-2">
          <p className="text-xs uppercase tracking-[0.24em] text-ink/50">Readiness</p>
          <p className="text-4xl font-semibold text-ink">{readiness.overall_score}/100</p>
          <p className="text-sm text-ink/70">Computed from project proof, interview readiness, learning progress, and practice reps.</p>
        </Panel>
        <Panel className="space-y-2">
          <p className="text-xs uppercase tracking-[0.24em] text-ink/50">Strongest signals</p>
          <p className="text-3xl font-semibold text-ink">{readiness.strongest_signals.length}</p>
          <p className="text-sm text-ink/70">Signals already working in your favor.</p>
        </Panel>
        <Panel className="space-y-2">
          <p className="text-xs uppercase tracking-[0.24em] text-ink/50">Gaps to close</p>
          <p className="text-3xl font-semibold text-ink">{readiness.gaps_to_close.length}</p>
          <p className="text-sm text-ink/70">Weakest links holding back stronger role alignment.</p>
        </Panel>
        <Panel className="space-y-2">
          <p className="text-xs uppercase tracking-[0.24em] text-ink/50">Questions loaded</p>
          <p className="text-3xl font-semibold text-ink">{questions.length}</p>
          <p className="text-sm text-ink/70">Use the roadmap below to decide which ones deserve reps this week.</p>
        </Panel>
      </div>

      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <div className="space-y-6">
          <Panel className="space-y-4">
            <SectionHeading eyebrow="Roadmap" title="Weekly rhythm" description="Generated from your current project proof, practice history, and saved market signals." />
            {roadmap.weekly_plan.map((item) => (
              <div key={item} className="rounded-2xl bg-mint p-4 text-sm text-ink">
                {item}
              </div>
            ))}
          </Panel>

          <Panel className="space-y-4">
            <SectionHeading eyebrow="Focus" title="Priority areas" description="These are the most important interview themes to sharpen next." />
            {roadmap.focus_areas.map((item) => (
              <div key={item} className="rounded-2xl bg-cream p-4 text-sm text-ink">
                {item}
              </div>
            ))}
          </Panel>

          <Panel className="space-y-4">
            <SectionHeading eyebrow="Readiness" title="Portfolio read" description="Use this to decide whether to invest the next hour in building, explaining, or rehearsing." />
            <div className="grid gap-3">
              {readiness.strongest_signals.map((item) => (
                <div key={item} className="rounded-2xl bg-white p-4 text-sm text-ink/80">
                  {item}
                </div>
              ))}
            </div>
            <div className="grid gap-3">
              {readiness.gaps_to_close.map((item) => (
                <div key={item} className="rounded-2xl bg-white p-4 text-sm text-ink/80">
                  {item}
                </div>
              ))}
            </div>
            <div className="grid gap-3">
              {readiness.next_best_moves.map((item) => (
                <div key={item} className="rounded-2xl bg-mint p-4 text-sm text-ink">
                  {item}
                </div>
              ))}
            </div>
          </Panel>
        </div>

        <Panel className="space-y-4">
          <SectionHeading eyebrow="Questions" title="Answer structure library" description="Use the roadmap rationale to choose which questions deserve a spoken rep this week." />
          {roadmap.rationale.length ? (
            <div className="grid gap-3">
              {roadmap.rationale.map((item) => (
                <div key={item} className="rounded-2xl bg-white p-4 text-sm text-ink/75">
                  {item}
                </div>
              ))}
            </div>
          ) : null}
          {questions.map((question) => (
            <div key={question.id} className="rounded-[24px] bg-cream p-5">
              <p className="text-xs uppercase tracking-[0.24em] text-ink/50">
                {question.category} | {question.difficulty}
              </p>
              <h3 className="mt-2 text-lg font-semibold text-ink">{question.question_text}</h3>
              <p className="mt-2 text-sm text-ink/70">{question.answer_outline_md}</p>
            </div>
          ))}
        </Panel>
      </div>
    </div>
  );
}
