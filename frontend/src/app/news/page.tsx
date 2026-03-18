import { NewsFeed } from "@/components/intelligence/news-feed";
import { SectionHeading } from "@/components/ui/section-heading";
import { portalApi } from "@/lib/api/portal";

export default async function NewsPage() {
  const newsItems = await portalApi.getNewsItems();

  return (
    <div className="space-y-6">
      <SectionHeading
        eyebrow="News Feed"
        title="AI engineering signals worth translating into action"
        description="Phase 2 turns the portal outward: track product-relevant releases, agent patterns, evaluation signals, and open-source momentum."
      />
      <NewsFeed initialItems={newsItems} />
    </div>
  );
}
