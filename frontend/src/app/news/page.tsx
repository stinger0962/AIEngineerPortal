import { Panel } from "@/components/ui/panel";
import { SectionHeading } from "@/components/ui/section-heading";

export default function NewsPage() {
  return (
    <Panel className="space-y-4">
      <SectionHeading eyebrow="News Feed" title="Phase 1 placeholder for intelligence ingestion." description="Live news aggregation is intentionally deferred so the MVP can stay focused on core learning and execution workflows." />
      <p className="text-sm text-ink/70">This page is ready for Phase 2 ingestion, summarization, and signal scoring work.</p>
    </Panel>
  );
}
