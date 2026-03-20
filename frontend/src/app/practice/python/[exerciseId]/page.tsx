import Link from "next/link";
import { notFound } from "next/navigation";

import { ExerciseAttemptForm } from "@/components/forms/exercise-attempt-form";
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
      <SectionHeading eyebrow="Exercise" title={detail.exercise.title} description={detail.exercise.prompt_md} />
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
      <Panel className="space-y-3">
        <SectionHeading
          eyebrow="Attempt history"
          title="Recent submissions"
          description={detail.review_prompt ?? "Use notes to make weaknesses explicit and repeatable."}
        />
        {detail.attempts.length ? (
          detail.attempts.map((attempt) => (
            <div key={attempt.id} className="rounded-2xl bg-cream p-4 text-sm text-ink">
              {attempt.status} / score {attempt.score} / {attempt.notes || "No notes"}
            </div>
          ))
        ) : (
          <p className="text-sm text-ink/70">No attempts yet.</p>
        )}
      </Panel>
    </div>
  );
}
