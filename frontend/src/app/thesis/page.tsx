import type { Metadata } from "next";

import { PipelineBoard } from "@/components/thesis/pipeline-board";
import { PIPELINE_META, PIPELINE_NODES } from "@/lib/thesis/pipeline";

export const metadata: Metadata = {
  title: "论文工厂",
  description: "C 刊论文全自动写作流水线：自动推进 · 人工闸门 · 不断 loop",
};

export default function ThesisPage() {
  return (
    <div className="space-y-6">
      {/* Hero */}
      <div className="relative overflow-hidden rounded-[28px] bg-gradient-to-br from-ink via-ink/95 to-pine p-5 text-cream lg:p-8">
        <div className="absolute -right-24 -top-24 h-80 w-80 rounded-full bg-teal/25 blur-3xl" />
        <div className="absolute -bottom-32 -left-16 h-72 w-72 rounded-full bg-ember/10 blur-3xl" />
        <div className="relative space-y-4">
          <span className="text-xs font-semibold uppercase tracking-[0.28em] text-teal">
            学 · Grow
          </span>
          <h1 className="font-display text-3xl leading-tight lg:text-4xl">
            {PIPELINE_META.title}
          </h1>
          <p className="max-w-xl text-[15px] leading-7 text-cream/60">
            {PIPELINE_META.subtitle} ——{PIPELINE_META.tagline}
          </p>
          <div className="flex flex-wrap gap-4 pt-2">
            <div className="min-w-[100px] rounded-2xl bg-white/10 px-5 py-3 text-center">
              <p className="text-2xl font-bold text-cream">{PIPELINE_NODES.length}</p>
              <p className="mt-1 text-[10px] uppercase tracking-wide text-cream/50">道工序</p>
            </div>
            <div className="min-w-[100px] rounded-2xl bg-white/10 px-5 py-3 text-center">
              <p className="text-2xl font-bold text-cream">{PIPELINE_NODES.length}</p>
              <p className="mt-1 text-[10px] uppercase tracking-wide text-cream/50">人工闸门</p>
            </div>
            <div className="min-w-[100px] rounded-2xl bg-white/10 px-5 py-3 text-center">
              <p className="text-2xl font-bold text-cream">2</p>
              <p className="mt-1 text-[10px] uppercase tracking-wide text-cream/50">篇 C 刊目标</p>
            </div>
          </div>
        </div>
      </div>

      {/* Pipeline */}
      <PipelineBoard />
    </div>
  );
}
