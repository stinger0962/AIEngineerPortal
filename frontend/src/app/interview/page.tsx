import { Panel } from "@/components/ui/panel";
import { SectionHeading } from "@/components/ui/section-heading";
import { portalApi } from "@/lib/api/portal";

export default async function InterviewPage() {
  const [questions, roadmap] = await Promise.all([portalApi.getInterviewQuestions(), portalApi.getInterviewRoadmap()]);

  return (
    <div className="space-y-6">
      <SectionHeading eyebrow="Interview Prep" title="Turn knowledge into answer structure." description="This center keeps system design, concepts, and behavioral framing in the same loop." />
      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <Panel className="space-y-3">
          <SectionHeading eyebrow="Roadmap" title="Weekly rhythm" description="Repetition matters more than cramming." />
          {roadmap.weekly_plan.map((item) => (
            <div key={item} className="rounded-2xl bg-mint p-4 text-sm text-ink">
              {item}
            </div>
          ))}
        </Panel>
        <Panel className="space-y-4">
          {questions.map((question) => (
            <div key={question.id} className="rounded-[24px] bg-cream p-5">
              <p className="text-xs uppercase tracking-[0.24em] text-ink/50">
                {question.category} · {question.difficulty}
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
