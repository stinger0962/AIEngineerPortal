import Link from "next/link";

import { Panel } from "@/components/ui/panel";
import { SectionHeading } from "@/components/ui/section-heading";
import { portalApi } from "@/lib/api/portal";

export default async function CoursesPage() {
  const courses = await portalApi.getCourses();

  return (
    <div className="space-y-6">
      <SectionHeading
        eyebrow="Course Hub"
        title="Guided tracks for turning study into visible execution."
        description="These tracks now organize the broader learning center into week-by-week milestones with linked lessons, drills, and project proof points."
      />
      <div className="grid gap-6 xl:grid-cols-2">
        {courses.map((course) => (
          <Panel key={course.id} className="space-y-4">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h3 className="font-display text-2xl text-ink">{course.title}</h3>
                <p className="mt-2 text-sm text-ink/70">{course.description}</p>
              </div>
              <div className="rounded-full bg-cream px-4 py-2 text-sm text-ink">{course.status}</div>
            </div>
            <div className="rounded-2xl bg-cream p-4 text-sm text-ink/75">
              <div className="text-xs uppercase tracking-[0.24em] text-rust">Track summary</div>
              <p className="mt-2 leading-6">
                {course.difficulty} / {course.estimated_hours} hours / {course.track_focus}
              </p>
            </div>
            <div className="space-y-2">
              {course.milestones_json.map((milestone) => (
                <div key={milestone.label} className="rounded-2xl bg-mint p-4 text-sm text-ink">
                  <div className="font-semibold">{milestone.label}</div>
                  <div className="mt-1 text-ink/70">{milestone.status}</div>
                  {milestone.goal ? <p className="mt-2 text-ink/75">{milestone.goal}</p> : null}
                </div>
              ))}
            </div>
            <Link href={`/courses/${course.slug}`} className="inline-flex rounded-full border border-ink/10 px-4 py-2 text-sm font-semibold">
              Open track
            </Link>
          </Panel>
        ))}
      </div>
    </div>
  );
}
