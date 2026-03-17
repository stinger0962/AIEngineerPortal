import Link from "next/link";
import { notFound } from "next/navigation";

import { Panel } from "@/components/ui/panel";
import { SectionHeading } from "@/components/ui/section-heading";
import { portalApi } from "@/lib/api/portal";

export default async function LearningPathPage({ params }: { params: Promise<{ pathSlug: string }> }) {
  const { pathSlug } = await params;
  const path = await portalApi.getPathBySlug(pathSlug);

  if (!path) {
    notFound();
  }

  return (
    <div className="space-y-6">
      <SectionHeading eyebrow="Learning Path" title={path.title} description={path.description} />
      <Panel className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
        <div className="space-y-3">
          <p className="rounded-full bg-mint px-4 py-2 text-sm text-ink">{path.completion_pct}% complete</p>
          <p className="text-sm text-ink/70">
            {path.level} · {path.estimated_hours} hours
          </p>
        </div>
        <div className="space-y-3">
          {path.lessons.map((lesson) => (
            <Link
              key={lesson.id}
              href={`/learn/lesson/${lesson.slug}`}
              className="block rounded-[24px] border border-ink/10 bg-white p-5 transition hover:border-ember/40"
            >
              <p className="text-xs uppercase tracking-[0.24em] text-ink/45">
                Lesson {lesson.order_index} {lesson.is_completed ? "· complete" : ""}
              </p>
              <h3 className="mt-2 text-lg font-semibold text-ink">{lesson.title}</h3>
              <p className="mt-2 text-sm text-ink/70">{lesson.summary}</p>
            </Link>
          ))}
        </div>
      </Panel>
    </div>
  );
}
