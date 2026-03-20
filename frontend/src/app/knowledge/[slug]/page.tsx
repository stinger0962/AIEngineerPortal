import { notFound } from "next/navigation";

import { LessonMarkdown } from "@/components/learning/lesson-markdown";
import { Panel } from "@/components/ui/panel";
import { SectionHeading } from "@/components/ui/section-heading";
import { portalApi } from "@/lib/api/portal";

export default async function KnowledgeDetailPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const article = await portalApi.getKnowledgeArticle(slug);

  if (!article) {
    notFound();
  }

  return (
    <div className="space-y-6">
      <SectionHeading eyebrow="Knowledge Note" title={article.title} description={article.summary} />
      <Panel className="space-y-4">
        <div className="grid gap-4 md:grid-cols-3">
          <div className="rounded-2xl bg-cream p-4 text-sm text-ink/80">
            <div className="text-xs uppercase tracking-[0.24em] text-rust">Category</div>
            <p className="mt-2 leading-6">{article.category}</p>
          </div>
          <div className="rounded-2xl bg-cream p-4 text-sm text-ink/80">
            <div className="text-xs uppercase tracking-[0.24em] text-rust">Tags</div>
            <p className="mt-2 leading-6">{article.tags_json.join(" · ")}</p>
          </div>
          <div className="rounded-2xl bg-cream p-4 text-sm text-ink/80">
            <div className="text-xs uppercase tracking-[0.24em] text-rust">Sources</div>
            <p className="mt-2 leading-6">{article.source_links_json.length} linked references</p>
          </div>
        </div>
        <article className="space-y-4">
          <LessonMarkdown content={article.content_md} />
        </article>
        <div className="rounded-2xl border border-ink/10 p-4 text-sm text-ink">
          <div className="font-semibold">Reference links</div>
          <div className="mt-3 flex flex-col gap-2">
            {article.source_links_json.map((link) => (
              <a key={link} href={link} target="_blank" rel="noreferrer" className="text-rust underline-offset-4 hover:underline">
                {link}
              </a>
            ))}
          </div>
        </div>
      </Panel>
    </div>
  );
}
