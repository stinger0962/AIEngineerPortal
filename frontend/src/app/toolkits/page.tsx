import Link from "next/link";
import { Flame, Layers, Search, Plus, AudioLines, Languages } from "lucide-react";

export default function ToolkitsPage() {
  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <span className="text-xs font-semibold uppercase tracking-[0.3em] text-[#bf6a1e]">
          蒸馏所 · Distill
        </span>
        <h1 className="font-display text-4xl mt-2 leading-[1.05]">
          <span className="bg-gradient-to-r from-[#d9531e] via-[#c9772a] to-[#c0892e] bg-clip-text text-transparent">
            万物皆可蒸馏。
          </span>{" "}
          <span className="text-ink/30 font-medium">Distill anything.</span>
        </h1>
        <p className="text-ink/60 text-sm mt-2 max-w-xl">
          一组把原始内容（视频、网页、文章）提炼为你真正用得上的形式的小工具。
        </p>
      </div>

      {/* Ready tools — equal height */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 items-stretch">
        {/* Forge — 焰铜 flame-copper */}
        <Link href="/toolkits/podcast" className="block h-full group">
          <div className="relative h-full flex flex-col overflow-hidden rounded-[26px] border border-ink/10 bg-gradient-to-br from-white to-[#fdf0e6] p-7 pl-8 transition-all duration-200 hover:-translate-y-1 hover:border-[#d9531e]/40 hover:shadow-[0_22px_46px_-18px_rgba(217,83,30,0.4)]">
            <span className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-[#d9531e] to-[#b8410f]" />
            <Flame className="pointer-events-none absolute -right-5 -bottom-6 w-36 h-36 text-[#d9531e] opacity-[0.05]" strokeWidth={1.5} />
            <div className="relative z-10 flex items-start gap-4">
              <div className="flex-shrink-0 w-[52px] h-[52px] rounded-[16px] bg-gradient-to-br from-[#f0894a] via-[#d9531e] to-[#b8410f] text-white flex items-center justify-center shadow-[0_6px_16px_-6px_rgba(217,83,30,0.6)]">
                <Flame className="w-[26px] h-[26px]" strokeWidth={2} />
              </div>
              <div>
                <div className="text-[12px] font-semibold tracking-wide text-ink/45">YOUTUBE → 播客</div>
                <h3 className="font-display text-[23px] font-semibold text-ink mt-0.5">
                  炼 <span className="text-ink/40 text-lg font-medium">Forge</span>
                </h3>
              </div>
            </div>
            <p className="relative z-10 text-[13.5px] leading-relaxed text-ink/[0.68] mt-4">
              把一条 YouTube 视频<span className="text-ink font-medium">炼</span>成一期中文播客 —— 单人讲述或双人对话，原生普通话配音。
            </p>
            <div className="relative z-10 flex flex-wrap gap-1.5 mt-auto pt-4">
              <span className="text-[11px] px-2.5 py-0.5 rounded-full font-medium bg-ink/5 text-ink/55">语音合成</span>
              <span className="text-[11px] px-2.5 py-0.5 rounded-full font-medium bg-ink/5 text-ink/55">AI 提炼</span>
              <span className="text-[11px] px-2.5 py-0.5 rounded-full font-semibold bg-[#d9531e]/[0.14] text-[#b8410f]">● Ready</span>
            </div>
          </div>
        </Link>

        {/* Loom — 赤金 amber-gold */}
        <Link href="/toolkits/summarize" className="block h-full group">
          <div className="relative h-full flex flex-col overflow-hidden rounded-[26px] border border-ink/10 bg-gradient-to-br from-white to-[#faf2e2] p-7 pl-8 transition-all duration-200 hover:-translate-y-1 hover:border-[#c0892e]/40 hover:shadow-[0_22px_46px_-18px_rgba(192,137,46,0.38)]">
            <span className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-[#c0892e] to-[#9c6a18]" />
            <Layers className="pointer-events-none absolute -right-5 -bottom-6 w-36 h-36 text-[#c0892e] opacity-[0.05]" strokeWidth={1.5} />
            <div className="relative z-10 flex items-start gap-4">
              <div className="flex-shrink-0 w-[52px] h-[52px] rounded-[16px] bg-gradient-to-br from-[#e0ad55] via-[#c0892e] to-[#9c6a18] text-white flex items-center justify-center shadow-[0_6px_16px_-6px_rgba(192,137,46,0.6)]">
                <Layers className="w-[26px] h-[26px]" strokeWidth={2} />
              </div>
              <div>
                <div className="text-[12px] font-semibold tracking-wide text-ink/45">内容 → 摘要</div>
                <h3 className="font-display text-[23px] font-semibold text-ink mt-0.5">
                  织 <span className="text-ink/40 text-lg font-medium">Loom</span>
                </h3>
              </div>
            </div>
            <p className="relative z-10 text-[13.5px] leading-relaxed text-ink/[0.68] mt-4">
              把文本、网页、YouTube 或微信文章<span className="text-ink font-medium">织</span>成结构化中文摘要 —— TL;DR、关键要点与核心收获。
            </p>
            <div className="relative z-10 flex flex-wrap gap-1.5 mt-auto pt-4">
              <span className="text-[11px] px-2.5 py-0.5 rounded-full font-medium bg-ink/5 text-ink/55">文本</span>
              <span className="text-[11px] px-2.5 py-0.5 rounded-full font-medium bg-ink/5 text-ink/55">网页</span>
              <span className="text-[11px] px-2.5 py-0.5 rounded-full font-medium bg-ink/5 text-ink/55">YouTube</span>
              <span className="text-[11px] px-2.5 py-0.5 rounded-full font-medium bg-ink/5 text-ink/55">微信</span>
              <span className="text-[11px] px-2.5 py-0.5 rounded-full font-semibold bg-[rgba(192,137,46,0.14)] text-[#9c6a18]">● Ready</span>
            </div>
          </div>
        </Link>

        {/* Scribe — 古铜 antique-bronze */}
        <Link href="/toolkits/scribe" className="block h-full group">
          <div className="relative h-full flex flex-col overflow-hidden rounded-[26px] border border-ink/10 bg-gradient-to-br from-white to-[#f7f0e6] p-7 pl-8 transition-all duration-200 hover:-translate-y-1 hover:border-[#9a6a34]/50 hover:shadow-[0_22px_46px_-18px_rgba(154,106,52,0.4)]">
            <span className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-[#9a6a34] to-[#7a521f]" />
            <AudioLines className="pointer-events-none absolute -right-5 -bottom-6 w-36 h-36 text-[#9a6a34] opacity-[0.05]" strokeWidth={1.5} />
            <div className="relative z-10 flex items-start gap-4">
              <div className="flex-shrink-0 w-[52px] h-[52px] rounded-[16px] bg-gradient-to-br from-[#b88a52] via-[#9a6a34] to-[#7a521f] text-white flex items-center justify-center shadow-[0_6px_16px_-6px_rgba(154,106,52,0.6)]">
                <AudioLines className="w-[26px] h-[26px]" strokeWidth={2} />
              </div>
              <div>
                <div className="text-[12px] font-semibold tracking-wide text-ink/45">YOUTUBE → 文字稿</div>
                <h3 className="font-display text-[23px] font-semibold text-ink mt-0.5">
                  录 <span className="text-ink/40 text-lg font-medium">Scribe</span>
                </h3>
              </div>
            </div>
            <p className="relative z-10 text-[13.5px] leading-relaxed text-ink/[0.68] mt-4">
              把无字幕的 YouTube 视频用 Whisper <span className="text-ink font-medium">录</span>成文字稿 —— 原语言逐字转写，可复制下载。
            </p>
            <div className="relative z-10 flex flex-wrap gap-1.5 mt-auto pt-4">
              <span className="text-[11px] px-2.5 py-0.5 rounded-full font-medium bg-ink/5 text-ink/55">Whisper</span>
              <span className="text-[11px] px-2.5 py-0.5 rounded-full font-medium bg-ink/5 text-ink/55">无字幕视频</span>
              <span className="text-[11px] px-2.5 py-0.5 rounded-full font-semibold bg-[rgba(154,106,52,0.15)] text-[#7a521f]">● Ready</span>
            </div>
          </div>
        </Link>

        {/* Dub — 朱赭 cinnabar-earth */}
        <Link href="/toolkits/dub" className="block h-full group">
          <div className="relative h-full flex flex-col overflow-hidden rounded-[26px] border border-ink/10 bg-gradient-to-br from-white to-[#fceee8] p-7 pl-8 transition-all duration-200 hover:-translate-y-1 hover:border-[#b9472f]/50 hover:shadow-[0_22px_46px_-18px_rgba(185,71,47,0.4)]">
            <span className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-[#b9472f] to-[#97351f]" />
            <Languages className="pointer-events-none absolute -right-5 -bottom-6 w-36 h-36 text-[#b9472f] opacity-[0.05]" strokeWidth={1.5} />
            <div className="relative z-10 flex items-start gap-4">
              <div className="flex-shrink-0 w-[52px] h-[52px] rounded-[16px] bg-gradient-to-br from-[#d2694a] via-[#b9472f] to-[#97351f] text-white flex items-center justify-center shadow-[0_6px_16px_-6px_rgba(185,71,47,0.6)]">
                <Languages className="w-[26px] h-[26px]" strokeWidth={2} />
              </div>
              <div>
                <div className="text-[12px] font-semibold tracking-wide text-ink/45">外语视频 → 中文配音</div>
                <h3 className="font-display text-[23px] font-semibold text-ink mt-0.5">
                  配 <span className="text-ink/40 text-lg font-medium">Dub</span>
                </h3>
              </div>
            </div>
            <p className="relative z-10 text-[13.5px] leading-relaxed text-ink/[0.68] mt-4">
              把外语 YouTube 视频<span className="text-ink font-medium">配</span>成中文旁白视频 —— 原声压低做背景，配音对齐时间轴。
            </p>
            <div className="relative z-10 flex flex-wrap gap-1.5 mt-auto pt-4">
              <span className="text-[11px] px-2.5 py-0.5 rounded-full font-medium bg-ink/5 text-ink/55">Whisper</span>
              <span className="text-[11px] px-2.5 py-0.5 rounded-full font-medium bg-ink/5 text-ink/55">中文 TTS</span>
              <span className="text-[11px] px-2.5 py-0.5 rounded-full font-semibold bg-[rgba(185,71,47,0.14)] text-[#97351f]">● Ready</span>
            </div>
          </div>
        </Link>
      </div>

      {/* Coming soon — refined panel */}
      <div className="flex flex-wrap items-center gap-4 rounded-[22px] border border-dashed border-ink/15 bg-gradient-to-br from-white/55 to-white/20 px-6 py-5">
        <span className="text-[12px] font-bold uppercase tracking-[0.16em] text-ink/40">即将上线</span>
        <div className="flex flex-wrap gap-2.5">
          <span className="inline-flex items-center gap-2 text-[13px] font-medium text-ink/50 bg-white/70 border border-ink/8 rounded-xl px-3 py-1.5">
            <Search className="w-4 h-4 opacity-55" strokeWidth={2} /> 职位扫描 Job Scanner
          </span>
          <span className="inline-flex items-center gap-2 text-[13px] font-medium text-ink/50 bg-white/70 border border-ink/8 rounded-xl px-3 py-1.5">
            <Plus className="w-4 h-4 opacity-55" strokeWidth={2} /> 申请新工具 Request a tool
          </span>
        </div>
        <span className="ml-auto text-[11px] uppercase tracking-[0.18em] text-ink/[0.32]">Coming soon</span>
      </div>
    </div>
  );
}
