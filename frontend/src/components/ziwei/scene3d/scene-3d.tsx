"use client";

import { Suspense, useState, useEffect, useRef } from "react";
import { Canvas } from "@react-three/fiber";
import { PerformanceMonitor } from "@react-three/drei";
import type { ZiweiChart } from "@/lib/ziwei/types";
import { Starfield } from "./starfield";
import { SceneEffects } from "./effects";
import { MysticBoard } from "./mystic-board";
import { CameraRig } from "./camera-rig";
import { PalaceInterior } from "./palace-interior";

export type Scene3DProps = {
  chart: ZiweiChart;
  selectedBranch: string | null;
  onSelectBranch: (branch: string | null) => void;
  onRenderError?: () => void;
  tourActive?: boolean;
};

export default function Scene3D({ chart, selectedBranch, onSelectBranch, onRenderError, tourActive }: Scene3DProps) {
  const [quality, setQuality] = useState<"high" | "low">("high");
  const disposedRef = useRef(false);
  useEffect(() => () => void (disposedRef.current = true), []);
  const selectedPalace = chart.palaces.find((p) => p.earthlyBranch === selectedBranch) ?? null;

  return (
    <Canvas
      dpr={quality === "high" ? [1, 1.75] : 1}
      camera={{ position: [0, 12, 10.5], fov: 42 }}
      style={{ background: "#050310" }}
      onPointerMissed={() => onSelectBranch(null)}
      onCreated={({ gl }) => {
        if (gl.getContext().isContextLost()) onRenderError?.();
        gl.domElement.addEventListener(
          "webglcontextlost",
          () => {
            if (!disposedRef.current) onRenderError?.(); // 卸载善后的 forceContextLoss 不算故障
          },
          { once: true },
        );
      }}
    >
      <PerformanceMonitor onDecline={() => setQuality("low")}>
        <color attach="background" args={["#050310"]} />
        <fog attach="fog" args={["#050310", 26, 60]} />
        <ambientLight intensity={0.55} />
        <directionalLight position={[6, 14, 8]} intensity={0.7} color="#cdb8ff" />

        <Suspense fallback={null}>
          <Starfield quality={quality} />
          <MysticBoard chart={chart} selectedBranch={selectedBranch} onSelectBranch={onSelectBranch} />
          {selectedPalace ? <PalaceInterior palace={selectedPalace} /> : null}
          <SceneEffects quality={quality} />
        </Suspense>

        <CameraRig selectedBranch={selectedBranch} smoothTime={tourActive ? 1.5 : 0.45} />
      </PerformanceMonitor>
    </Canvas>
  );
}
