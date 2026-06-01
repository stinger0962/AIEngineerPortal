import { ToolkitCard } from "@/components/toolkits/toolkit-card";

export default function ToolkitsPage() {
  return (
    <div className="space-y-8">
      <div>
        <span className="text-xs font-semibold uppercase tracking-[0.28em] text-ember">
          Toolkits
        </span>
        <h1 className="font-display text-3xl text-cream mt-1">Your toolkit.</h1>
        <p className="text-cream/50 text-sm mt-1">
          Standalone utilities to accelerate your AI engineering journey.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <ToolkitCard
          icon="🎙"
          name="YouTube Podcast"
          description="Paste a YouTube URL and get a digested Chinese podcast episode — single narrator or two-person dialogue."
          href="/toolkits/podcast"
          tags={[
            { label: "TTS", variant: "default" },
            { label: "AI digest", variant: "default" },
            { label: "Ready", variant: "ready" },
          ]}
        />
        <ToolkitCard
          icon="📄"
          name="Doc Builder"
          description="Generate structured documents from raw notes and outlines."
          comingSoon
          tags={[{ label: "Coming soon", variant: "soon" }]}
        />
        <ToolkitCard
          icon="🔍"
          name="Job Scanner"
          description="Analyse job description fit against your resume and target role."
          comingSoon
          tags={[{ label: "Coming soon", variant: "soon" }]}
        />
        <ToolkitCard
          icon="＋"
          name="Request a tool"
          description="Have an idea for a useful utility? Let me know."
          comingSoon
          tags={[]}
        />
      </div>
    </div>
  );
}
