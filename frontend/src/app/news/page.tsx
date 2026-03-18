import Link from "next/link";

import { Panel } from "@/components/ui/panel";
import { SectionHeading } from "@/components/ui/section-heading";
import { portalApi } from "@/lib/api/portal";

export default async function NewsPage() {
  const newsItems = await portalApi.getNewsItems();

  return (
    <div className="space-y-6">
      <Panel className="space-y-4">
        <SectionHeading
          eyebrow="News Feed"
          title="AI engineering signals worth translating into action"
          description="Phase 2 starts turning the portal outward: track product-relevant releases, agent patterns, evaluation signals, and open-source momentum."
        />
        <div className="grid gap-4 md:grid-cols-3">
          <div className="rounded-2xl bg-cream p-4">
            <p className="text-xs uppercase tracking-[0.24em] text-ink/50">Items tracked</p>
            <p className="mt-2 text-3xl font-semibold text-ink">{newsItems.length}</p>
          </div>
          <div className="rounded-2xl bg-cream p-4">
            <p className="text-xs uppercase tracking-[0.24em] text-ink/50">High-signal updates</p>
            <p className="mt-2 text-3xl font-semibold text-ink">{newsItems.filter((item) => item.signal_score >= 85).length}</p>
          </div>
          <div className="rounded-2xl bg-cream p-4">
            <p className="text-xs uppercase tracking-[0.24em] text-ink/50">Saved for later</p>
            <p className="mt-2 text-3xl font-semibold text-ink">{newsItems.filter((item) => item.is_saved).length}</p>
          </div>
        </div>
      </Panel>

      <div className="grid gap-4">
        {newsItems.map((item) => (
          <Panel key={item.id} className="space-y-3">
            <div className="flex flex-wrap items-center gap-2 text-xs uppercase tracking-[0.24em] text-ink/50">
              <span>{item.source_name}</span>
              <span>Signal {item.signal_score}</span>
              <span>{new Date(item.published_at).toLocaleDateString()}</span>
            </div>
            <div className="flex items-start justify-between gap-4">
              <div>
                <h3 className="font-display text-2xl text-ink">{item.title}</h3>
                <p className="mt-2 text-sm text-ink/70">{item.summary}</p>
              </div>
              {item.is_saved ? <span className="rounded-full bg-mint px-3 py-1 text-xs font-semibold text-ink">Saved</span> : null}
            </div>
            <div className="flex flex-wrap gap-2">
              {item.tags_json.map((tag) => (
                <span key={tag} className="rounded-full border border-ink/10 px-3 py-1 text-xs text-ink/70">
                  {tag}
                </span>
              ))}
            </div>
            <Link href={item.source_url} className="inline-flex rounded-full border border-ink/10 px-4 py-2 text-sm font-semibold" target="_blank">
              Open source
            </Link>
          </Panel>
        ))}
      </div>
    </div>
  );
}
