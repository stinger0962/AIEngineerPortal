import { ToolkitCard } from "@/components/toolkits/toolkit-card";

export default function ToolkitsPage() {
  return (
    <div className="space-y-8">
      <div>
        <span className="text-xs font-semibold uppercase tracking-[0.28em] text-ember">
          Toolkits
        </span>
        <h1 className="font-display text-3xl text-ink mt-1">Your toolkit.</h1>
        <p className="text-ink/50 text-sm mt-1">
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
          icon="📝"
          name="内容摘要 Summarize"
          description="粘贴文本、网页或 YouTube 链接，获得结构化中文摘要 — TL;DR、关键要点与核心收获。"
          href="/toolkits/summarize"
          tags={[
            { label: "AI summary", variant: "default" },
            { label: "Web · YouTube", variant: "default" },
            { label: "Ready", variant: "ready" },
          ]}
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
