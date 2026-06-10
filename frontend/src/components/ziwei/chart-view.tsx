"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { ChartGrid2D } from "@/components/ziwei/chart-grid-2d";
import type { ZiweiChart } from "@/lib/ziwei/types";

const Scene3D = dynamic(() => import("./scene3d/scene-3d"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full min-h-[480px] items-center justify-center">
      <p className="animate-pulse text-sm text-violet-300/60">正在汇聚星辰……</p>
    </div>
  ),
});

const VIEW_KEY = "ziwei-view-mode";

function detectWebGL(): boolean {
  try {
    const canvas = document.createElement("canvas");
    return Boolean(canvas.getContext("webgl2") ?? canvas.getContext("webgl"));
  } catch {
    return false;
  }
}

export function ChartView({ chart }: { chart: ZiweiChart }) {
  // null = 检测中（SSR 安全：首帧渲染 2D，挂载后决定）
  const [webgl, setWebgl] = useState<boolean | null>(null);
  const [mode, setMode] = useState<"3d" | "2d">("3d");
  const [selectedBranch, setSelectedBranch] = useState<string | null>(null);

  useEffect(() => {
    setWebgl(detectWebGL());
    const saved = window.localStorage.getItem(VIEW_KEY);
    if (saved === "2d" || saved === "3d") setMode(saved);
  }, []);

  const switchMode = (next: "3d" | "2d") => {
    setMode(next);
    window.localStorage.setItem(VIEW_KEY, next);
  };

  const show3d = mode === "3d" && webgl === true;

  return (
    <div className="relative overflow-hidden rounded-[28px] border border-violet-500/20 bg-[#050310] shadow-[0_20px_50px_rgba(91,33,182,0.25)]">
      {/* 模式切换（WebGL 不可用时隐藏 3D 选项） */}
      {webgl !== false ? (
        <div className="absolute right-3 top-3 z-10 flex gap-1 rounded-full border border-violet-500/30 bg-[#120a2e]/80 p-1 backdrop-blur">
          {(["3d", "2d"] as const).map((m) => (
            <button
              key={m}
              type="button"
              onClick={() => switchMode(m)}
              className={`rounded-full px-3 py-1 text-xs font-semibold transition-colors ${
                mode === m ? "bg-violet-600 text-white" : "text-violet-300/70 hover:text-violet-100"
              }`}
            >
              {m === "3d" ? "3D 星盘" : "2D 方盘"}
            </button>
          ))}
        </div>
      ) : null}

      {show3d ? (
        <div className="h-[72vh] min-h-[480px]">
          <Scene3D chart={chart} selectedBranch={selectedBranch} onSelectBranch={setSelectedBranch} />
        </div>
      ) : (
        <div className="p-2 sm:p-3">
          {webgl === false ? (
            <p className="px-2 pb-2 text-xs text-violet-300/60">当前设备不支持 WebGL，已切换为 2D 命盘。</p>
          ) : null}
          <ChartGrid2D chart={chart} />
        </div>
      )}
    </div>
  );
}
