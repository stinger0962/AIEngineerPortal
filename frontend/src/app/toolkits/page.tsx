import type { ReactNode } from "react";
import Link from "next/link";
import { Flame, Layers, Search, Plus, AudioLines, Languages, type LucideIcon } from "lucide-react";

// 每个工具一套暖色签名色（同时用于卡片预览 + 工具页内部，保证点开前后一致）。
// 四色同属铜火暖系：炼焰铜 / 织赤金 / 录古铜 / 配朱赭。
type Hue = { main: string; deep: string; light: string };
type Tool = {
  href: string;
  icon: LucideIcon;
  char: string;
  en: string;
  eyebrow: string;
  desc: ReactNode;
  tags: string[];
  c: Hue;
};

const bold = (s: string) => (
  <span className="font-medium" style={{ color: "var(--cd)" }}>
    {s}
  </span>
);

const TOOLS: Tool[] = [
  {
    href: "/toolkits/podcast",
    icon: Flame,
    char: "炼",
    en: "Forge",
    eyebrow: "YOUTUBE → 播客",
    desc: <>把一条 YouTube 视频{bold("炼")}成一期中文播客 —— 单人讲述或双人对话，原生普通话配音。</>,
    tags: ["语音合成", "AI 提炼"],
    c: { main: "#d9531e", deep: "#b8410f", light: "#f0894a" },
  },
  {
    href: "/toolkits/summarize",
    icon: Layers,
    char: "织",
    en: "Loom",
    eyebrow: "内容 → 摘要",
    desc: <>把文本、网页、YouTube 或微信文章{bold("织")}成结构化中文摘要 —— TL;DR、关键要点与核心收获。</>,
    tags: ["文本", "网页", "YouTube", "微信"],
    c: { main: "#c0892e", deep: "#9c6a18", light: "#e0ad55" },
  },
  {
    href: "/toolkits/scribe",
    icon: AudioLines,
    char: "录",
    en: "Scribe",
    eyebrow: "YOUTUBE → 文字稿",
    desc: <>把无字幕的 YouTube 视频用 Whisper {bold("录")}成文字稿 —— 原语言逐字转写，可复制下载。</>,
    tags: ["Whisper", "无字幕视频"],
    c: { main: "#9a6a34", deep: "#7a521f", light: "#b88a52" },
  },
  {
    href: "/toolkits/dub",
    icon: Languages,
    char: "配",
    en: "Dub",
    eyebrow: "外语视频 → 中文配音",
    desc: <>把外语 YouTube 视频{bold("配")}成中文旁白视频 —— 原声压低做背景，配音对齐时间轴。</>,
    tags: ["Whisper", "中文 TTS"],
    c: { main: "#b9472f", deep: "#97351f", light: "#d2694a" },
  },
];

export default function ToolkitsPage() {
  return (
    <div className="space-y-8">
      <style>{`
        .tk-card:hover {
          border-color: color-mix(in srgb, var(--c) 45%, transparent) !important;
          box-shadow: 0 22px 46px -18px color-mix(in srgb, var(--c) 58%, transparent);
        }
      `}</style>

      {/* Header */}
      <div>
        <span className="text-xs font-semibold uppercase tracking-[0.3em] text-[#bf6a1e]">蒸馏所 · Distill</span>
        <h1 className="font-display text-4xl mt-2 leading-[1.05]">
          <span className="bg-gradient-to-r from-[#d9531e] via-[#c9772a] to-[#c0892e] bg-clip-text text-transparent">
            万物皆可蒸馏。
          </span>{" "}
          <span className="text-[#9a6a30]/40 font-medium">Distill anything.</span>
        </h1>
        <p className="text-[#5c4326]/70 text-sm mt-2 max-w-xl">
          一组把原始内容（视频、网页、文章）提炼为你真正用得上的形式的小工具。
        </p>
      </div>

      {/* Ready tools — each card in its own tool's signature color */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 items-stretch">
        {TOOLS.map((t) => {
          const Icon = t.icon;
          return (
            <Link key={t.href} href={t.href} className="block h-full group">
              <div
                className="tk-card relative h-full flex flex-col overflow-hidden rounded-[26px] border p-7 pl-8 transition-all duration-200 hover:-translate-y-1"
                style={
                  {
                    "--c": t.c.main,
                    "--cd": t.c.deep,
                    borderColor: `${t.c.main}26`,
                    background: `linear-gradient(135deg, #ffffff, ${t.c.light}22)`,
                  } as React.CSSProperties
                }
              >
                <span className="absolute left-0 top-0 bottom-0 w-1" style={{ background: `linear-gradient(${t.c.main}, ${t.c.deep})` }} />
                <Icon className="pointer-events-none absolute -right-5 -bottom-6 w-36 h-36 opacity-[0.06]" style={{ color: t.c.main }} strokeWidth={1.5} />
                <div className="relative z-10 flex items-start gap-4">
                  <div
                    className="flex-shrink-0 w-[52px] h-[52px] rounded-[16px] text-white flex items-center justify-center"
                    style={{ background: `linear-gradient(135deg, ${t.c.light}, ${t.c.main}, ${t.c.deep})`, boxShadow: `0 6px 16px -6px ${t.c.main}99` }}
                  >
                    <Icon className="w-[26px] h-[26px]" strokeWidth={2} />
                  </div>
                  <div>
                    <div className="text-[12px] font-semibold tracking-wide" style={{ color: t.c.deep, opacity: 0.82 }}>
                      {t.eyebrow}
                    </div>
                    <h3 className="font-display text-[23px] font-semibold mt-0.5" style={{ color: t.c.deep }}>
                      {t.char} <span className="text-lg font-medium" style={{ color: t.c.main, opacity: 0.62 }}>{t.en}</span>
                    </h3>
                  </div>
                </div>
                <p className="relative z-10 text-[13.5px] leading-relaxed mt-4 text-[#5c4326]/85">{t.desc}</p>
                <div className="relative z-10 flex flex-wrap gap-1.5 mt-auto pt-4">
                  {t.tags.map((tag) => (
                    <span key={tag} className="text-[11px] px-2.5 py-0.5 rounded-full font-medium" style={{ background: `${t.c.main}1a`, color: t.c.deep }}>
                      {tag}
                    </span>
                  ))}
                  <span className="text-[11px] px-2.5 py-0.5 rounded-full font-semibold" style={{ background: `${t.c.main}29`, color: t.c.deep }}>
                    ● Ready
                  </span>
                </div>
              </div>
            </Link>
          );
        })}
      </div>

      {/* Coming soon */}
      <div className="flex flex-wrap items-center gap-4 rounded-[22px] border border-dashed border-[#c0732e]/20 bg-white/45 px-6 py-5">
        <span className="text-[12px] font-bold uppercase tracking-[0.16em] text-[#9a6a30]/55">即将上线</span>
        <div className="flex flex-wrap gap-2.5">
          <span className="inline-flex items-center gap-2 text-[13px] font-medium text-[#5c4326]/60 bg-white/70 border border-[#c0732e]/12 rounded-xl px-3 py-1.5">
            <Search className="w-4 h-4 opacity-55" strokeWidth={2} /> 职位扫描 Job Scanner
          </span>
          <span className="inline-flex items-center gap-2 text-[13px] font-medium text-[#5c4326]/60 bg-white/70 border border-[#c0732e]/12 rounded-xl px-3 py-1.5">
            <Plus className="w-4 h-4 opacity-55" strokeWidth={2} /> 申请新工具 Request a tool
          </span>
        </div>
        <span className="ml-auto text-[11px] uppercase tracking-[0.18em] text-[#9a6a30]/35">Coming soon</span>
      </div>
    </div>
  );
}
