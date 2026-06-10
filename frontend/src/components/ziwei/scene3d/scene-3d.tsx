"use client";

import { Suspense, useState } from "react";
import { Canvas } from "@react-three/fiber";
import { CameraControls, PerformanceMonitor } from "@react-three/drei";
import type { ZiweiChart } from "@/lib/ziwei/types";
import { Starfield } from "./starfield";
import { SceneEffects } from "./effects";
import { MysticBoard } from "./mystic-board";

export type Scene3DProps = {
  chart: ZiweiChart;
  selectedBranch: string | null;
  onSelectBranch: (branch: string | null) => void;
};

export default function Scene3D({ chart, selectedBranch, onSelectBranch }: Scene3DProps) {
  const [quality, setQuality] = useState<"high" | "low">("high");

  return (
    <Canvas
      dpr={quality === "high" ? [1, 1.75] : 1}
      camera={{ position: [0, 12, 10.5], fov: 42 }}
      style={{ background: "#050310" }}
    >
      <PerformanceMonitor onDecline={() => setQuality("low")}>
        <color attach="background" args={["#050310"]} />
        <fog attach="fog" args={["#050310", 26, 60]} />
        <ambientLight intensity={0.55} />
        <directionalLight position={[6, 14, 8]} intensity={0.7} color="#cdb8ff" />

        <Suspense fallback={null}>
          <Starfield quality={quality} />
          <MysticBoard chart={chart} selectedBranch={selectedBranch} onSelectBranch={onSelectBranch} />
          <SceneEffects quality={quality} />
        </Suspense>

        <CameraControls makeDefault minDistance={6} maxDistance={28} maxPolarAngle={Math.PI * 0.46} />
      </PerformanceMonitor>
    </Canvas>
  );
}
