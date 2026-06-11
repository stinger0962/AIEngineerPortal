"use client";

import { useCallback, useRef } from "react";
import type { CameraCommand, OracleSegment } from "@/lib/ziwei/api";
import type { ZiweiChart } from "@/lib/ziwei/types";
import type { TermInfo } from "../term-card";

type ReplayDeps = {
  chart: ZiweiChart;
  onText: (full: string) => void;                  // 累进文本回调（更新该条消息可见内容）
  onFocusBranch: (branch: string | null) => void;
  onTerm: (t: TermInfo | null) => void;
  reducedMotion: boolean;
};

const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

const PALACE_ALIASES: Record<string, string> = { 交友: "仆役", 仆役: "交友" };

function branchOf(chart: ZiweiChart, palaceName: string): string | null {
  const hit =
    chart.palaces.find((p) => p.name === palaceName) ??
    chart.palaces.find((p) => p.name === PALACE_ALIASES[palaceName]);
  if (!hit) {
    console.warn(`segment-replay: 未知宫位「${palaceName}」，镜头跳过`);
    return null;
  }
  return hit.earthlyBranch;
}

export function useSegmentReplay() {
  const cancelRef = useRef(false);

  const cancel = useCallback(() => {
    cancelRef.current = true;
  }, []);

  const fireCommand = (cmd: CameraCommand, deps: ReplayDeps) => {
    if (cmd.type === "focus_palace") {
      const branch = branchOf(deps.chart, cmd.palace);
      if (branch) deps.onFocusBranch(branch);
    } else if (cmd.type === "overview") {
      deps.onFocusBranch(null);
    } else if (cmd.type === "explain_term") {
      deps.onTerm({ term: cmd.term, explanation: cmd.explanation });
    }
  };

  const play = useCallback(async (segments: OracleSegment[], deps: ReplayDeps) => {
    cancelRef.current = false;
    let acc = "";
    for (const seg of segments) {
      if (cancelRef.current) break;
      const text = seg.text ?? "";
      if (deps.reducedMotion || text.length === 0) {
        // 空文本段（如纯镜头指令）不追加分隔符，避免瞬时多空行
        if (text.length > 0) {
          acc += (acc ? "\n\n" : "") + text;
          deps.onText(acc);
        }
      } else {
        acc += acc ? "\n\n" : "";
        for (let i = 0; i < text.length; i += 4) {
          if (cancelRef.current) break;
          acc += text.slice(i, i + 4);
          deps.onText(acc);
          await sleep(12);
        }
      }
      if (cancelRef.current) break;
      for (const cmd of seg.commands) fireCommand(cmd, deps);
      if (!deps.reducedMotion) await sleep(650);
    }
    const full = segments.map((s) => s.text).filter(Boolean).join("\n\n");
    deps.onText(full);
  }, []);

  return { play, cancel };
}
