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

function branchOf(chart: ZiweiChart, palaceName: string): string | null {
  return chart.palaces.find((p) => p.name === palaceName)?.earthlyBranch ?? null;
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
        acc += (acc ? "\n\n" : "") + text;
        deps.onText(acc);
      } else {
        acc += acc ? "\n\n" : "";
        for (let i = 0; i < text.length; i += 2) {
          if (cancelRef.current) break;
          acc += text.slice(i, i + 2);
          deps.onText(acc);
          await sleep(18);
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
