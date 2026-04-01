import Link from "next/link";

import { Panel } from "@/components/ui/panel";
import { SectionHeading } from "@/components/ui/section-heading";
import { portalApi } from "@/lib/api/portal";

export default async function LearnPage() {
  const [paths, articles] = await Promise.all([
    portalApi.getLearningPaths(),
    portalApi.getKnowledgeArticles(),
  ]);

  return (
    <div className="space-y-8">
      <SectionHeading eyebrow="Learn" title="Structured progression, not fragmented browsing." description="Paths for sequential study. Reference articles for deep dives on specific topics." />

      {/* Learning Paths */}
      <div>
        <h2 className="mb-4 text-xs font-semibold uppercase tracking-[0.28em] text-ember">Learning Paths</h2>
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

      {/* Reference Articles */}
      <div>
        <h2 className="mb-4 text-xs font-semibold uppercase tracking-[0.28em] text-ember">Reference Articles</h2>
        <div className="grid gap-4 xl:grid-cols-3 lg:grid-cols-2">
          {articles.map((article) => (
            <Link key={article.id} href={`/knowledge/${article.slug}`}>
              <Panel className="space-y-2 hover:shadow-lg transition-shadow cursor-pointer h-full">
                <span className="text-xs uppercase tracking-wide text-pine">{article.category}</span>
                <h4 className="font-display text-lg text-ink">{article.title}</h4>
                <p className="text-sm text-ink/60 line-clamp-2">{article.summary}</p>
              </Panel>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
