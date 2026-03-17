import { Panel } from "@/components/ui/panel";
import { SectionHeading } from "@/components/ui/section-heading";

export default function JobsPage() {
  return (
    <Panel className="space-y-4">
      <SectionHeading eyebrow="Jobs" title="Phase 1 placeholder for opportunity tracking." description="Live job ingestion, fit scoring, and application tracking are queued for the next major delivery phase." />
      <p className="text-sm text-ink/70">The portal shell includes this route now so future intelligence modules can slot into the same navigation model.</p>
    </Panel>
  );
}
