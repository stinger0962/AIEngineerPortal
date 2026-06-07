import Link from "next/link";
import { Flame, Layers, Search, Plus } from "lucide-react";

export default function ToolkitsPage() {
  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <span className="text-xs font-semibold uppercase tracking-[0.3em] text-ember">
          蒸馏所 · Distill
        </span>
        <h1 className="font-display text-4xl text-ink mt-2 leading-[1.05]">
          万物皆可蒸馏。{" "}
          <span className="text-ink/35 font-medium">Distill anything.</span>
        </h1>
        <p className="text-ink/60 text-sm mt-2 max-w-xl">
          一组把原始内容（视频、网页、文章）提炼为你真正用得上的形式的小工具。
        </p>
      </div>

      {/* Ready tools */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Forge */}
        <Link href="/toolkits/podcast" className="block group">
          <div className="relative overflow-hidden rounded-[24px] border border-ink/10 bg-white/85 shadow-panel p-7 pl-8 transition-all duration-150 hover:-translate-y-0.5 hover:border-ember/40 hover:shadow-lg">
            <span className="absolute left-0 top-0 bottom-0 w-1 bg-ember" />
            <div className="flex items-start gap-4">
              <div className="flex-shrink-0 w-[50px] h-[50px] rounded-[15px] bg-ember/12 text-ember flex items-center justify-center">
                <Flame className="w-[25px] h-[25px]" strokeWidth={2} />
              </div>
              <div>
                <div className="text-[12px] font-semibold tracking-wide text-ink/45">
                  YOUTUBE → 播客
                </div>
                <h3 className="font-display text-[22px] font-semibold text-ink mt-0.5">
                  炼 <span className="text-ink/40 text-lg font-medium">Forge</span>
                </h3>
              </div>
            </div>
            <p className="text-[13.5px] leading-relaxed text-ink/65 mt-3.5 mb-4">
              把一条 YouTube 视频<span className="text-ink font-medium">炼</span>成一期中文播客 —— 单人讲述或双人对话，原生普通话配音。
            </p>
            <div className="flex flex-wrap gap-1.5">
              <span className="text-[11px] px-2.5 py-0.5 rounded-full font-medium bg-ink/6 text-ink/55">语音合成</span>
              <span className="text-[11px] px-2.5 py-0.5 rounded-full font-medium bg-ink/6 text-ink/55">AI 提炼</span>
              <span className="text-[11px] px-2.5 py-0.5 rounded-full font-semibold bg-ember/14 text-ember">● Ready</span>
            </div>
          </div>
        </Link>

        {/* Loom */}
        <Link href="/toolkits/summarize" className="block group">
          <div className="relative overflow-hidden rounded-[24px] border border-ink/10 bg-white/85 shadow-panel p-7 pl-8 transition-all duration-150 hover:-translate-y-0.5 hover:border-pine/40 hover:shadow-lg">
            <span className="absolute left-0 top-0 bottom-0 w-1 bg-pine" />
            <div className="flex items-start gap-4">
              <div className="flex-shrink-0 w-[50px] h-[50px] rounded-[15px] bg-pine/12 text-pine flex items-center justify-center">
                <Layers className="w-[25px] h-[25px]" strokeWidth={2} />
              </div>
              <div>
                <div className="text-[12px] font-semibold tracking-wide text-ink/45">
                  内容 → 摘要
                </div>
                <h3 className="font-display text-[22px] font-semibold text-ink mt-0.5">
                  织 <span className="text-ink/40 text-lg font-medium">Loom</span>
                </h3>
              </div>
            </div>
            <p className="text-[13.5px] leading-relaxed text-ink/65 mt-3.5 mb-4">
              把文本、网页、YouTube 或微信文章<span className="text-ink font-medium">织</span>成结构化中文摘要 —— TL;DR、关键要点与核心收获。
            </p>
            <div className="flex flex-wrap gap-1.5">
              <span className="text-[11px] px-2.5 py-0.5 rounded-full font-medium bg-ink/6 text-ink/55">文本</span>
              <span className="text-[11px] px-2.5 py-0.5 rounded-full font-medium bg-ink/6 text-ink/55">网页</span>
              <span className="text-[11px] px-2.5 py-0.5 rounded-full font-medium bg-ink/6 text-ink/55">YouTube</span>
              <span className="text-[11px] px-2.5 py-0.5 rounded-full font-medium bg-ink/6 text-ink/55">微信</span>
              <span className="text-[11px] px-2.5 py-0.5 rounded-full font-semibold bg-pine/12 text-pine">● Ready</span>
            </div>
          </div>
        </Link>
      </div>

      {/* Coming soon — slim strip */}
      <div className="flex items-center gap-5 px-6 py-4 rounded-[20px] border border-dashed border-ink/15 bg-white/40">
        <div className="flex items-center gap-2 text-sm font-medium text-ink/45">
          <Search className="w-[17px] h-[17px] opacity-60" strokeWidth={2} />
          职位扫描 Job Scanner
        </div>
        <span className="w-1 h-1 rounded-full bg-ink/20" />
        <div className="flex items-center gap-2 text-sm font-medium text-ink/45">
          <Plus className="w-[17px] h-[17px] opacity-60" strokeWidth={2} />
          申请新工具 Request a tool
        </div>
        <span className="ml-auto text-[11px] uppercase tracking-[0.18em] text-ink/35">
          开发中 · Coming soon
        </span>
      </div>
    </div>
  );
}
