import Link from "next/link";
import { notFound } from "next/navigation";

import { Panel } from "@/components/ui/panel";
import { SectionHeading } from "@/components/ui/section-heading";
import { portalApi } from "@/lib/api/portal";

export default async function CourseDetailPage({ params }: { params: Promise<{ courseSlug: string }> }) {
  const { courseSlug } = await params;
  const course = await portalApi.getCourse(courseSlug);

  if (!course) {
    notFound();
  }

  return (
    <div className="space-y-6">
      <SectionHeading eyebrow="Course Track" title={course.title} description={course.description} />
      <Panel className="space-y-4">
        <p className="text-sm text-ink/70">
          {course.difficulty} / {course.estimated_hours} hours / {course.track_focus}
        </p>
        <div className="grid gap-4 md:grid-cols-3">
          <div className="rounded-2xl bg-cream p-4 text-sm text-ink/80">
            <div className="text-xs uppercase tracking-[0.24em] text-rust">Track posture</div>
            <p className="mt-2 leading-6">Use this course like a 4-week sprint: learn the core material, do the linked drills, and convert one artifact into portfolio proof.</p>
          </div>
          <div className="rounded-2xl bg-cream p-4 text-sm text-ink/80">
            <div className="text-xs uppercase tracking-[0.24em] text-rust">Primary goal</div>
            <p className="mt-2 leading-6">Build a clean transition path from software engineering leverage into AI engineer execution, systems thinking, and interview proof.</p>
          </div>
          <div className="rounded-2xl bg-cream p-4 text-sm text-ink/80">
            <div className="text-xs uppercase tracking-[0.24em] text-rust">Completion test</div>
            <p className="mt-2 leading-6">You should be able to explain one real AI system, one live project, and one clear next-step gap without vague hand-waving.</p>
          </div>
        </div>
      </Panel>
      <div className="space-y-4">
        {course.milestones_json.map((milestone, index) => (
          <Panel key={milestone.label} className="space-y-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.24em] text-rust">Milestone {index + 1}</p>
                <h3 className="mt-2 font-display text-2xl text-ink">{milestone.label}</h3>
              </div>
              <div className="rounded-full bg-cream px-4 py-2 text-sm text-ink">{milestone.status}</div>
            </div>
            {milestone.goal ? (
              <div className="rounded-2xl bg-mint p-4 text-sm text-ink">
                <div className="font-semibold">Goal</div>
                <p className="mt-2 text-ink/75">{milestone.goal}</p>
              </div>
            ) : null}
            {milestone.outcome ? (
              <div className="rounded-2xl bg-cream p-4 text-sm text-ink">
                <div className="font-semibold">Expected outcome</div>
                <p className="mt-2 text-ink/75">{milestone.outcome}</p>
              </div>
            ) : null}
            <div className="grid gap-4 md:grid-cols-3">
              <div className="rounded-2xl border border-ink/10 p-4 text-sm text-ink">
                <div className="font-semibold">Primary learning path</div>
                {milestone.path_slug && milestone.path_title ? (
                  <Link href={`/learn/${milestone.path_slug}`} className="mt-2 inline-flex text-rust underline-offset-4 hover:underline">
                    {milestone.path_title}
                  </Link>
                ) : (
                  <p className="mt-2 text-ink/70">No linked path yet.</p>
                )}
              </div>
              <div className="rounded-2xl border border-ink/10 p-4 text-sm text-ink">
                <div className="font-semibold">Suggested drills</div>
                {milestone.exercise_slugs && milestone.exercise_slugs.length > 0 ? (
                  <ul className="mt-2 space-y-1 text-ink/75">
                    {milestone.exercise_slugs.map((exerciseSlug) => (
                      <li key={exerciseSlug}>{exerciseSlug}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-2 text-ink/70">No linked drills for this milestone.</p>
                )}
              </div>
              <div className="rounded-2xl border border-ink/10 p-4 text-sm text-ink">
                <div className="font-semibold">Project proof point</div>
                {milestone.project_slug ? (
                  <Link href={`/projects/${milestone.project_slug}`} className="mt-2 inline-flex text-rust underline-offset-4 hover:underline">
                    {milestone.project_slug}
                  </Link>
                ) : (
                  <p className="mt-2 text-ink/70">No linked project yet.</p>
                )}
              </div>
            </div>
            {milestone.lesson_slugs && milestone.lesson_slugs.length > 0 ? (
              <div className="rounded-2xl border border-ink/10 p-4 text-sm text-ink">
                <div className="font-semibold">Lesson sequence</div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {milestone.lesson_slugs.map((lessonSlug) => (
                    <Link
                      key={lessonSlug}
                      href={`/learn/lesson/${lessonSlug}`}
                      className="rounded-full border border-ink/10 px-3 py-2 text-xs font-semibold text-ink/80 transition hover:bg-cream"
                    >
                      {lessonSlug}
                    </Link>
                  ))}
                </div>
              </div>
            ) : null}
            {milestone.deliverable ? (
              <div className="rounded-2xl bg-white p-4 text-sm text-ink">
                <div className="font-semibold">Deliverable</div>
                <p className="mt-2 text-ink/75">{milestone.deliverable}</p>
              </div>
            ) : null}
            {milestone.why_it_matters ? (
              <div className="rounded-2xl border border-gold/40 bg-gold/10 p-4 text-sm text-ink">
                <div className="font-semibold">Why this matters</div>
                <p className="mt-2 text-ink/80">{milestone.why_it_matters}</p>
              </div>
            ) : null}
          </Panel>
        ))}
      </div>
    </div>
  );
}
