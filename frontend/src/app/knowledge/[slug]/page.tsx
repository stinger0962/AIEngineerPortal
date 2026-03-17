import { notFound } from "next/navigation";

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
        {article.content_md.split("\n").map((line, index) => (
          <p key={`${line}-${index}`} className="text-sm leading-7 text-ink/80">
            {line}
          </p>
        ))}
      </Panel>
    </div>
  );
}
