import Link from "next/link";

import { Panel } from "@/components/ui/panel";
import { SectionHeading } from "@/components/ui/section-heading";
import { portalApi } from "@/lib/api/portal";
import { titleCase } from "@/lib/utils";

export default async function PracticePage() {
  const exercises = await portalApi.getExercises();

  return (
    <div className="space-y-6">
      <SectionHeading eyebrow="Python Practice" title="Hands-on drills tuned for AI engineering." description="Practice implementation muscle memory instead of passively reviewing notes." />
      <div className="grid gap-6 xl:grid-cols-2">
        {exercises.map((exercise) => (
          <Panel key={exercise.id} className="space-y-4">
            <div className="flex items-center justify-between gap-4">
              <h3 className="text-xl font-semibold text-ink">{exercise.title}</h3>
              <span className="rounded-full bg-mint px-3 py-1 text-xs uppercase tracking-[0.24em] text-ink">
                {exercise.difficulty}
              </span>
            </div>
            <p className="text-sm text-ink/70">{titleCase(exercise.category)}</p>
            <p className="text-sm text-ink/75">{exercise.prompt_md}</p>
            <Link href={`/practice/python/${exercise.id}`} className="inline-flex rounded-full bg-ink px-4 py-2 text-sm font-semibold text-white">
              Open exercise
            </Link>
          </Panel>
        ))}
      </div>
    </div>
  );
}
