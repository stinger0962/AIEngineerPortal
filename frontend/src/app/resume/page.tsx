import { ResumeBuilder } from "@/components/resume/resume-builder";
import { Panel } from "@/components/ui/panel";

export default function ResumePage() {
  return (
    <div className="space-y-6">
      <div className="relative overflow-hidden rounded-[28px] bg-gradient-to-br from-ink via-ink/95 to-pine p-5 lg:p-8 text-cream">
        <div className="absolute top-0 right-0 w-64 h-64 bg-ember/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/4" />
        <div className="relative space-y-3">
          <span className="text-xs font-semibold uppercase tracking-[0.28em] text-ember">Resume Builder</span>
          <h1 className="font-display text-3xl lg:text-4xl leading-tight">Generate your AI Engineer resume.</h1>
          <p className="text-cream/60 text-[15px] leading-7 max-w-2xl">
            Fill in your experience and let Claude craft a tailored resume. Your portal learning data is automatically included to showcase your AI engineering skills.
          </p>
        </div>
      </div>
      <Panel>
        <ResumeBuilder />
      </Panel>
    </div>
  );
}
