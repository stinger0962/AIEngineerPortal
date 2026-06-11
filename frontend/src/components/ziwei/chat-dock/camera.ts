"use client";

import type { CameraCommand } from "@/lib/ziwei/api";
import type { ZiweiChart } from "@/lib/ziwei/types";
import type { TermInfo } from "../term-card";

// iztro 命盘把交友宫记作「仆役」；模型可能说任一名，双向兜底匹配
const PALACE_ALIASES: Record<string, string> = { 交友: "仆役", 仆役: "交友" };

export function branchOf(chart: ZiweiChart, palaceName: string): string | null {
  const hit =
    chart.palaces.find((p) => p.name === palaceName) ??
    chart.palaces.find((p) => p.name === PALACE_ALIASES[palaceName]);
  if (!hit) {
    console.warn(`chat-dock: 未知宫位「${palaceName}」，镜头跳过`);
    return null;
  }
  return hit.earthlyBranch;
}

type FireDeps = {
  chart: ZiweiChart;
  onFocusBranch: (branch: string | null) => void;
  onTerm: (t: TermInfo | null) => void;
};

/** 即时执行一条镜头/UI 指令：飞入宫位、回总览、弹术语卡。 */
export function fireCamera(cmd: CameraCommand, deps: FireDeps): void {
  if (cmd.type === "focus_palace") {
    const branch = branchOf(deps.chart, cmd.palace);
    if (branch) deps.onFocusBranch(branch);
  } else if (cmd.type === "overview") {
    deps.onFocusBranch(null);
  } else if (cmd.type === "explain_term") {
    deps.onTerm({ term: cmd.term, explanation: cmd.explanation });
  }
}
