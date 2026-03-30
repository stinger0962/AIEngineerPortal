import { Panel } from "@/components/ui/panel";
import { SectionHeading } from "@/components/ui/section-heading";
import { CopilotChat } from "@/components/copilot/copilot-chat";

export default function CopilotPage() {
  return (
    <section className="space-y-6">
      <SectionHeading
        eyebrow="AI Study Copilot"
        title="Your AI engineering learning companion"
        description="Ask questions about AI engineering concepts. I'll search your lessons, exercises, and knowledge articles to give personalized answers."
      />

      <Panel>
        <CopilotChat />
      </Panel>
    </section>
  );
}
