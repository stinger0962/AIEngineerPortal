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
          {titleCase(detail.exercise.category)} · {detail.exercise.difficulty}
        </p>
        <ExerciseAttemptForm exerciseId={detail.exercise.id} starterCode={detail.exercise.starter_code} />
      </Panel>
      <Panel className="space-y-3">
        <SectionHeading eyebrow="Attempt history" title="Recent submissions" description="Use notes to make weaknesses explicit and repeatable." />
        {detail.attempts.length ? (
          detail.attempts.map((attempt) => (
            <div key={attempt.id} className="rounded-2xl bg-cream p-4 text-sm text-ink">
              {attempt.status} · score {attempt.score} · {attempt.notes || "No notes"}
            </div>
          ))
        ) : (
          <p className="text-sm text-ink/70">No attempts yet.</p>
        )}
      </Panel>
    </div>
  );
}
