"use client";
import type { CameraCommand } from "@/lib/ziwei/api";
import type { TermInfo } from "@/components/ziwei/term-card";

/** 求签的镜头执行器：3D 是单签筒、无宫位落点，故 focus/overview 仅用于收尾清术语卡；term 弹卡。 */
export function makeQianFireCommand(onTerm: (t: TermInfo | null) => void) {
  return (cmd: CameraCommand) => {
    if (cmd.type === "explain_term") onTerm({ term: cmd.term, explanation: cmd.explanation });
    else if (cmd.type === "overview") onTerm(null); // 收尾
  };
}
