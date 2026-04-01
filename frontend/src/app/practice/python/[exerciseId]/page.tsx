import Link from "next/link";
import { notFound } from "next/navigation";

import { ExerciseAttemptForm } from "@/components/forms/exercise-attempt-form";
import { VariationSection } from "@/components/forms/variation-section";
import { LessonMarkdown } from "@/components/learning/lesson-markdown";
import { Panel } from "@/components/ui/panel";
import { SectionHeading } from "@/components/ui/section-heading";
import { portalApi } from "@/lib/api/portal";
import { titleCase } from "@/lib/utils";

export default async function ExerciseDetailPage({ params }: { params: Promise<{ exerciseId: string }> }) {
  const { exerciseId } = await params;
  const detail = await portalApi.getExercise(Number(exerciseId));

  if (!detail?.exercise) {
    notFound();
  }

  return (
    <div className="space-y-6">
      <SectionHeading eyebrow="Exercise" title={detail.exercise.title} description="" />
      <LessonMarkdown content={detail.exercise.prompt_md} />
      <Panel className="space-y-4">
        <p className="text-sm text-ink/70">
          {titleCase(detail.exercise.category)} / {detail.exercise.difficulty}
          {detail.exercise.progression_label ? ` / ${detail.exercise.progression_label}` : ""}
        </p>
        <div className="grid gap-4 md:grid-cols-3">
          <div className="rounded-2xl bg-cream p-4 text-sm text-ink/80">
            <div className="text-xs uppercase tracking-[0.24em] text-rust">Practice stage</div>
            <p className="mt-2 leading-6">{detail.exercise.practice_stage ?? "General drill"}</p>
          </div>
          <div className="rounded-2xl bg-cream p-4 text-sm text-ink/80">
            <div className="text-xs uppercase tracking-[0.24em] text-rust">Hint</div>
            <p className="mt-2 leading-6">{detail.exercise.hint_md ?? "Keep the solution explicit and reviewable."}</p>
          </div>
          <div className="rounded-2xl bg-cream p-4 text-sm text-ink/80">
            <div className="text-xs uppercase tracking-[0.24em] text-rust">Next drill</div>
            {detail.exercise.next_exercise_id && detail.exercise.next_exercise_title ? (
              <Link href={`/practice/python/${detail.exercise.next_exercise_id}`} className="mt-2 inline-flex text-rust underline-offset-4 hover:underline">
                {detail.exercise.next_exercise_title}
              </Link>
            ) : (
              <p className="mt-2 leading-6">This is the end of the current mini-sequence.</p>
            )}
          </div>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <div className="rounded-2xl border border-ink/10 p-4 text-sm text-ink">
            <div className="font-semibold">Success criteria</div>
            {detail.exercise.success_criteria_json?.length ? (
              <ul className="mt-2 space-y-2 text-ink/75">
                {detail.exercise.success_criteria_json.map((item) => (
                  <li key={item}>- {item}</li>
                ))}
              </ul>
            ) : (
              <p className="mt-2 text-ink/70">Make the solution explicit, debuggable, and easy to explain.</p>
            )}
          </div>
          <div className="rounded-2xl border border-ink/10 p-4 text-sm text-ink">
            <div className="font-semibold">Review checklist</div>
            {detail.exercise.review_checklist_json?.length ? (
              <ul className="mt-2 space-y-2 text-ink/75">
                {detail.exercise.review_checklist_json.map((item) => (
                  <li key={item}>- {item}</li>
                ))}
              </ul>
            ) : (
              <p className="mt-2 text-ink/70">Review where the boundary is, what gets validated, and what would be hard to debug later.</p>
            )}
          </div>
        </div>
        {detail.exercise.related_lesson_slugs?.length ? (
          <div className="rounded-2xl border border-ink/10 p-4 text-sm text-ink">
            <div className="font-semibold">Related lessons</div>
            <div className="mt-3 flex flex-wrap gap-2">
              {detail.exercise.related_lesson_slugs.map((slug, index) => (
                <Link
                  key={slug}
                  href={`/learn/lesson/${slug}`}
                  className="rounded-full border border-ink/10 px-3 py-2 text-xs font-semibold text-ink/80 transition hover:bg-cream"
                >
                  {detail.exercise.related_lesson_titles?.[index] ?? slug}
                </Link>
              ))}
            </div>
          </div>
        ) : null}
        <ExerciseAttemptForm exerciseId={detail.exercise.id} starterCode={detail.exercise.starter_code} />
      </Panel>
      <Panel className="space-y-4">
        <SectionHeading
          eyebrow="Practice"
          title="Generate a variation"
          description="Generate a new exercise variation to deepen understanding or practice a related concept."
        />
        <VariationSection exerciseId={detail.exercise.id} />
      </Panel>
      <Panel className="space-y-3">
        <SectionHeading
          eyebrow="Attempt history"
          title="Recent submissions"
          description={detail.review_prompt ?? "Use notes to make weaknesses explicit and repeatable."}
        />
        {detail.attempts.length ? (
          detail.attempts.map((attempt) => {
            const scoreBadge =
              attempt.score >= 85
                ? "bg-green-100 text-green-700"
                : attempt.score >= 70
                  ? "bg-amber-100 text-amber-700"
                  : "bg-red-100 text-red-700";
            return (
              <div key={attempt.id} className="rounded-2xl bg-cream p-4 text-sm text-ink flex items-start justify-between gap-4">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-medium capitalize">{attempt.status}</span>
                    {attempt.ai_feedback_id && (
                      <span className="rounded-full bg-ember/10 px-2 py-0.5 text-xs font-medium text-ember">
                        AI graded
                      </span>
                    )}
                  </div>
                  <p className="mt-1 text-ink/60">{attempt.notes || "No notes"}</p>
                </div>
                <span className={`shrink-0 rounded-full px-3 py-1 text-xs font-bold ${scoreBadge}`}>
                  {attempt.score}/100
                </span>
              </div>
            );
          })
        ) : (
          <p className="text-sm text-ink/70">No attempts yet.</p>
        )}
      </Panel>
      {detail.attempts.length ? (
        <Panel className="space-y-4">
          <SectionHeading
            eyebrow="Reference"
            title="Correct answer and review notes"
            description="Use the reference solution to compare structure, not just syntax."
          />
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-3 rounded-2xl bg-[#0f172a] p-4 text-sm text-slate-100">
              <div className="font-semibold text-slate-200">Reference solution</div>
              <pre className="overflow-x-auto whitespace-pre-wrap leading-6">
                <code>{detail.exercise.solution_code}</code>
              </pre>
            </div>
            <div className="rounded-2xl bg-cream p-4 text-sm text-ink">
              <div className="font-semibold">Why this answer works</div>
              <LessonMarkdown content={detail.exercise.explanation_md} />
            </div>
          </div>
        </Panel>
      ) : null}
    </div>
  );
}
