import Link from "next/link";

import { Panel } from "@/components/ui/panel";
import { SectionHeading } from "@/components/ui/section-heading";
import { portalApi } from "@/lib/api/portal";

export default async function LearnPage() {
  const paths = await portalApi.getLearningPaths();

  return (
    <div className="space-y-6">
      <SectionHeading eyebrow="Learning Center" title="Structured progression, not fragmented browsing." description="Every path is tuned toward applied AI engineering work and interview leverage." />
      <div className="grid gap-6 xl:grid-cols-2">
        {paths.map((path) => (
          <Panel key={path.id} className="space-y-4">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h3 className="font-display text-2xl text-ink">{path.title}</h3>
                <p className="mt-2 text-sm text-ink/70">{path.description}</p>
              </div>
              <div className="rounded-full bg-mint px-4 py-2 text-sm text-ink">{path.completion_pct}% complete</div>
            </div>
            <div className="flex gap-2 text-xs uppercase tracking-[0.24em] text-ink/50">
              <span>{path.level}</span>
              <span>{path.estimated_hours}h</span>
            </div>
            <div className="space-y-2">
              {path.lessons.slice(0, 3).map((lesson) => (
                <div key={lesson.id} className="rounded-2xl bg-cream p-4 text-sm text-ink">
                  {lesson.title}
                </div>
              ))}
            </div>
            <Link href={`/learn/${path.slug}`} className="inline-flex rounded-full bg-ink px-5 py-3 text-sm font-semibold text-white">
              Open path
            </Link>
          </Panel>
        ))}
      </div>
    </div>
  );
}
