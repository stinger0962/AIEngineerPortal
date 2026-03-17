import { Panel } from "@/components/ui/panel";
import { SectionHeading } from "@/components/ui/section-heading";

export default function SettingsPage() {
  return (
    <Panel className="space-y-4">
      <SectionHeading eyebrow="Settings" title="Single-user personalization defaults." description="Auth and full preference management are out of scope for Phase 1, but the portal documents the current assumptions." />
      <ul className="space-y-2 text-sm text-ink/70">
        <li>Prioritize Python depth, LLM application engineering, RAG, agents, evaluation, and deployment.</li>
        <li>Keep project-building early in the roadmap.</li>
        <li>Surface interview prep as progress becomes more visible.</li>
      </ul>
    </Panel>
  );
}
