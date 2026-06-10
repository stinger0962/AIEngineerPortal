"use client";

import type { ReactNode } from "react";
import { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Text } from "@react-three/drei";
import * as THREE from "three";
import type { ZiweiChart } from "@/lib/ziwei/types";
import { CELL_W, CELL_D, PLATE_H } from "./layout";
import { PalacePlate } from "./palace-plate";
import { SihuaBeams } from "./sihua-beams";
import { useReducedMotion } from "./camera-rig";
import { ZIWEI_FONT_URL, ZIWEI_GLYPHS } from "./glyphs";

function CenterPlate({ chart }: { chart: ZiweiChart }) {
  const lines = [
    chart.fiveElementsClass,
    chart.chineseDate,
    `公历 ${chart.solarDate}`,
    `农历 ${chart.lunarDate}`,
    `${chart.time}（${chart.timeRange}）`,
    `命主 ${chart.soul} · 身主 ${chart.body}`,
    `${chart.zodiac} · ${chart.sign}`,
  ];
  return (
    <group>
      <mesh position={[0, -0.02, 0]}>
        <boxGeometry args={[CELL_W * 2 - 0.34, PLATE_H, CELL_D * 2 - 0.34]} />
        <meshStandardMaterial color="#08041a" emissive="#fbbf24" emissiveIntensity={0.05} roughness={0.7} metalness={0.3} />
      </mesh>
      {lines.map((line, i) => (
        <Text
          key={i}
          font={ZIWEI_FONT_URL}
          characters={ZIWEI_GLYPHS}
          fontSize={i === 0 ? 0.5 : 0.26}
          color={i === 0 ? "#fde68a" : "#b6a3e0"}
          anchorX="center"
          anchorY="middle"
          position={[0, PLATE_H / 2 + 0.012, -2.1 + i * 0.62 + (i > 0 ? 0.25 : 0)]}
          rotation={[-Math.PI / 2, 0, 0]}
        >
          {line}
        </Text>
      ))}
    </group>
  );
}

export type MysticBoardProps = {
  chart: ZiweiChart;
  selectedBranch: string | null;
  onSelectBranch: (branch: string | null) => void;
  children?: ReactNode; // 四化光束等盘级装饰（Task 5）
};

export function MysticBoard({ chart, selectedBranch, onSelectBranch, children }: MysticBoardProps) {
  const groupRef = useRef<THREE.Group>(null);
  const progressRef = useRef(0);
  const reducedMotion = useReducedMotion();

  useFrame((_, delta) => {
    if (!groupRef.current) return;
    if (reducedMotion) progressRef.current = 1;
    progressRef.current = Math.min(1, progressRef.current + delta / 1.2);
    const eased = 1 - Math.pow(1 - progressRef.current, 3);
    groupRef.current.position.y = -1.2 * (1 - eased);
  });

  return (
    <group ref={groupRef}>
      {chart.palaces.map((palace) => (
        <PalacePlate
          key={palace.earthlyBranch}
          palace={palace}
          isSoulPalace={palace.earthlyBranch === chart.earthlyBranchOfSoulPalace}
          dimmed={selectedBranch !== null && selectedBranch !== palace.earthlyBranch}
          onSelect={(branch) => onSelectBranch(branch)}
        />
      ))}
      <CenterPlate chart={chart} />
      <SihuaBeams chart={chart} visible={selectedBranch === null} />
      {children}
    </group>
  );
}
