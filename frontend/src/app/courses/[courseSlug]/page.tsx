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
          {course.difficulty} · {course.estimated_hours} hours · {course.track_focus}
        </p>
        {course.milestones_json.map((milestone) => (
          <div key={milestone.label} className="rounded-2xl bg-cream p-4 text-sm text-ink">
            {milestone.label} · {milestone.status}
          </div>
        ))}
      </Panel>
    </div>
  );
}
