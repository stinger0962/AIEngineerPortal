"use client";

import { Suspense } from "react";
import { Canvas } from "@react-three/fiber";
import { Text } from "@react-three/drei";
import type { ZiweiChart } from "@/lib/ziwei/types";
import { ZIWEI_FONT_URL, ZIWEI_GLYPHS } from "./glyphs";

export type Scene3DProps = {
  chart: ZiweiChart;
  selectedBranch: string | null;
  onSelectBranch: (branch: string | null) => void;
};

/** 最小场景：验证 Canvas + 中文字体管线。后续任务在此基础上展开三层场景。 */
export default function Scene3D({ chart }: Scene3DProps) {
  return (
    <Canvas dpr={[1, 1.75]} camera={{ position: [0, 12, 10.5], fov: 42 }} style={{ background: "#050310" }}>
      <Suspense fallback={null}>
        <Text font={ZIWEI_FONT_URL} characters={ZIWEI_GLYPHS} fontSize={1} color="#d8c8ff" position={[0, 0, 0]}>
          {chart.fiveElementsClass}
        </Text>
      </Suspense>
    </Canvas>
  );
}
