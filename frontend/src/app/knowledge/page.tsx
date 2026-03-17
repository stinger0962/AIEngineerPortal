import Link from "next/link";

import { Panel } from "@/components/ui/panel";
import { SectionHeading } from "@/components/ui/section-heading";
import { portalApi } from "@/lib/api/portal";

export default async function KnowledgePage() {
  const articles = await portalApi.getKnowledgeArticles();

  return (
    <div className="space-y-6">
      <SectionHeading eyebrow="Knowledge Hub" title="Searchable notes, comparisons, and architecture patterns." description="Keep a practical reference library close to your active project work." />
      <div className="grid gap-6 xl:grid-cols-2">
        {articles.map((article) => (
          <Panel key={article.id} className="space-y-4">
            <p className="text-xs uppercase tracking-[0.24em] text-ember">{article.category}</p>
            <h3 className="font-display text-2xl text-ink">{article.title}</h3>
            <p className="text-sm text-ink/70">{article.summary}</p>
            <Link href={`/knowledge/${article.slug}`} className="inline-flex rounded-full border border-ink/10 px-4 py-2 text-sm font-semibold">
              Read note
            </Link>
          </Panel>
        ))}
      </div>
    </div>
  );
}
