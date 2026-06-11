"use client";

import dynamic from "next/dynamic";
import { useEffect, useLayoutEffect, useState } from "react";
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
  // 每次探测用全新 canvas：getContext("webgl2") 失败也会锁定该 canvas 的 context 模式，
  // 复用同一个 canvas 会让后续 "webgl" 探测恒为 null（老设备被误判为不支持）
  const probe = (type: "webgl2" | "webgl") => {
    try {
      return Boolean(document.createElement("canvas").getContext(type));
    } catch {
      return false;
    }
  };
  return probe("webgl2") || probe("webgl");
}

export function ChartView({
  chart,
  selectedBranch,
  onSelectBranch,
}: {
  chart: ZiweiChart;
  selectedBranch: string | null;
  onSelectBranch: (b: string | null) => void;
}) {
  // null = 检测中（SSR 安全：首帧渲染 2D，挂载后决定）
  const [webgl, setWebgl] = useState<boolean | null>(null);
  const [mode, setMode] = useState<"3d" | "2d">("3d");
  const [renderFailed, setRenderFailed] = useState(false);

  // useLayoutEffect：在首帧绘制前定下 webgl/mode，避免 2D 盘闪现一帧再切 3D
  useLayoutEffect(() => {
    setWebgl(detectWebGL());
    try {
      const saved = window.localStorage.getItem(VIEW_KEY);
      if (saved === "2d" || saved === "3d") setMode(saved);
    } catch {
      // 隐私模式下 localStorage 可能直接 throw——持久化本就尽力而为
    }
  }, []);

  const switchMode = (next: "3d" | "2d") => {
    setMode(next);
    onSelectBranch(null); // 模式往返不保留选宫（约定：3D→2D→3D 回到总览）
    if (next === "3d") setRenderFailed(false); // 用户主动重试 3D 时清除渲染失败标记
    try {
      window.localStorage.setItem(VIEW_KEY, next);
    } catch {
      // 同上
    }
  };

  const show3d = mode === "3d" && webgl === true && !renderFailed;

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onSelectBranch(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <div className="relative overflow-hidden rounded-[28px] border border-violet-500/20 bg-[#050310] shadow-[0_20px_50px_rgba(91,33,182,0.25)]">
      {/* 模式切换（WebGL 不可用时隐藏 3D 选项） */}
      {webgl !== false ? (
        <div className="absolute right-3 top-3 z-10 flex gap-1 rounded-full border border-violet-500/30 bg-[#120a2e]/80 p-1 backdrop-blur">
          {(["3d", "2d"] as const).map((m) => (
            <button
              key={m}
              type="button"
              aria-pressed={mode === m}
              onClick={() => switchMode(m)}
              className={`rounded-full px-3 py-2 text-xs font-semibold transition-colors ${
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
          <Scene3D
            chart={chart}
            selectedBranch={selectedBranch}
            onSelectBranch={onSelectBranch}
            onRenderError={() => setRenderFailed(true)}
          />
          {show3d && selectedBranch ? (
            <button
              type="button"
              onClick={() => onSelectBranch(null)}
              className="absolute left-3 top-3 z-10 rounded-full border border-violet-500/40 bg-[#120a2e]/85 px-4 py-2 text-xs font-semibold text-violet-100 backdrop-blur transition-colors hover:bg-violet-600/40"
            >
              ← 返回总览
            </button>
          ) : null}
        </div>
      ) : (
        <div className="p-2 sm:p-3">
          {renderFailed ? (
            <p className="px-2 pb-2 text-xs text-violet-300/60">3D 渲染中断，已切换 2D 命盘。</p>
          ) : webgl === false ? (
            <p className="px-2 pb-2 text-xs text-violet-300/60">当前设备不支持 WebGL，已切换为 2D 命盘。</p>
          ) : null}
          <ChartGrid2D chart={chart} />
        </div>
      )}
    </div>
  );
}
