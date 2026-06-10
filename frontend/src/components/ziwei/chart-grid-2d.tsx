"use client";

/**
 * WebGL 降级 / Phase 1 主视图：2D 暗夜方盘。
 * 刻意只渲染主星+辅星——adjectiveStars/changsheng12/ages 留给后续 3D 单宫内景与 AI 上下文，
 * 以保证小格子里的可读性（spec 原则「不懂紫微的人也能看懂」）。
 */

import { MUTAGEN_STYLES } from "@/lib/ziwei/constants";
import type { ZiweiChart, ZiweiPalace, ZiweiStar } from "@/lib/ziwei/types";

/** 地支 → 4×4 网格位置（row / col，从 1 开始） */
const BRANCH_GRID: Record<string, { row: number; col: number }> = {
  巳: { row: 1, col: 1 },
  午: { row: 1, col: 2 },
  未: { row: 1, col: 3 },
  申: { row: 1, col: 4 },
  辰: { row: 2, col: 1 },
  酉: { row: 2, col: 4 },
  卯: { row: 3, col: 1 },
  戌: { row: 3, col: 4 },
  寅: { row: 4, col: 1 },
  丑: { row: 4, col: 2 },
  子: { row: 4, col: 3 },
  亥: { row: 4, col: 4 },
};

function StarBadge({ star, major }: { star: ZiweiStar; major: boolean }) {
  return (
    <span className={`inline-flex items-center gap-0.5 ${major ? "text-[13px] font-semibold text-violet-100" : "text-[11px] text-violet-300/80"}`}>
      {star.name}
      {star.brightness ? <sup className="text-[9px] text-violet-300/60">{star.brightness}</sup> : null}
      {star.mutagen ? (
        <span className={`rounded px-0.5 text-[9px] leading-tight ${MUTAGEN_STYLES[star.mutagen] ?? "bg-violet-500/80 text-white"}`}>
          {star.mutagen}
        </span>
      ) : null}
    </span>
  );
}

function PalaceCell({ palace, isSoulPalace }: { palace: ZiweiPalace; isSoulPalace: boolean }) {
  const pos = BRANCH_GRID[palace.earthlyBranch];
  if (!pos) {
    console.warn(`ChartGrid2D: 未知地支「${palace.earthlyBranch}」，宫位未渲染（chart_json 可能来自非 zh-CN 排盘）`);
    return null;
  }
  return (
    <div
      style={{ gridRow: pos.row, gridColumn: pos.col }}
      className={`relative flex flex-col rounded-lg border p-1.5 transition-colors ${
        isSoulPalace
          ? "border-amber-400/60 bg-gradient-to-br from-violet-900/60 to-[#160b38] shadow-[0_0_14px_rgba(251,191,36,0.25)]"
          : "border-violet-500/25 bg-gradient-to-br from-violet-950/40 to-[#0d0722]"
      }`}
    >
      <div className="flex flex-wrap gap-x-1.5 gap-y-0.5">
        {palace.majorStars.map((s) => (
          <StarBadge key={s.name} star={s} major />
        ))}
      </div>
      <div className="mt-0.5 flex flex-wrap gap-x-1 gap-y-0">
        {palace.minorStars.map((s) => (
          <StarBadge key={s.name} star={s} major={false} />
        ))}
      </div>
      <div className="mt-auto flex items-end justify-between pt-1">
        <span className="text-[10px] text-violet-300/50">
          {palace.decadal.range[0]}-{palace.decadal.range[1]}
        </span>
        <div className="text-right">
          <span className="text-[12px] font-semibold text-violet-100">
            {palace.name}
            {palace.isBodyPalace ? <span className="ml-0.5 rounded bg-amber-500/80 px-0.5 text-[9px] text-white">身</span> : null}
          </span>
          <div className="text-[10px] text-violet-300/50">
            {palace.heavenlyStem}
            {palace.earthlyBranch}
          </div>
        </div>
      </div>
    </div>
  );
}

function CenterCell({ chart }: { chart: ZiweiChart }) {
  return (
    <div
      style={{ gridRow: "2 / 4", gridColumn: "2 / 4" }}
      className="flex flex-col items-center justify-center gap-1 rounded-lg border border-amber-400/30 bg-[#08041a] p-3 text-center"
    >
      <p className="text-sm font-semibold tracking-[0.2em] text-amber-200/90">{chart.fiveElementsClass}</p>
      <p className="text-[11px] text-violet-200/70">{chart.chineseDate}</p>
      <p className="text-[11px] text-violet-200/70">
        公历 {chart.solarDate} · 农历 {chart.lunarDate}
      </p>
      <p className="text-[11px] text-violet-200/70">
        {chart.time}（{chart.timeRange}）
      </p>
      <p className="text-[11px] text-violet-300/60">
        命主 {chart.soul} · 身主 {chart.body}
      </p>
      <p className="text-[11px] text-violet-300/60">
        {chart.zodiac} · {chart.sign}
      </p>
    </div>
  );
}

export function ChartGrid2D({ chart }: { chart: ZiweiChart }) {
  return (
    <div
      aria-label="紫微斗数命盘"
      className="overflow-x-auto rounded-[28px] border border-violet-500/20 bg-[#0a0618] p-2 shadow-[0_20px_50px_rgba(91,33,182,0.25)] sm:p-3"
    >
      <div className="grid aspect-square min-w-[480px] grid-cols-4 grid-rows-4 gap-1">
        {chart.palaces.map((palace) => (
          <PalaceCell
            key={palace.earthlyBranch}
            palace={palace}
            isSoulPalace={palace.earthlyBranch === chart.earthlyBranchOfSoulPalace}
          />
        ))}
        <CenterCell chart={chart} />
      </div>
    </div>
  );
}
