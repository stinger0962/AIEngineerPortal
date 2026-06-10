"use client";

import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { QuadraticBezierLine } from "@react-three/drei";
import type { QuadraticBezierLineRef } from "@react-three/drei";
import type { ZiweiChart } from "@/lib/ziwei/types";
import { MUTAGEN_COLORS, branchPosition } from "./layout";

type BeamSpec = { branch: string; mutagen: string; color: string };

/** 找出生年四化所在的四个宫（扫描全部星曜的 mutagen 标记） */
function findMutagenPalaces(chart: ZiweiChart): BeamSpec[] {
  const beams: BeamSpec[] = [];
  for (const palace of chart.palaces) {
    for (const star of [...palace.majorStars, ...palace.minorStars, ...palace.adjectiveStars]) {
      if (star.mutagen && MUTAGEN_COLORS[star.mutagen]) {
        beams.push({ branch: palace.earthlyBranch, mutagen: star.mutagen, color: MUTAGEN_COLORS[star.mutagen] });
      }
    }
  }
  return beams;
}

function Beam({ spec }: { spec: BeamSpec }) {
  const target = branchPosition(spec.branch);
  // QuadraticBezierLine forwards a QuadraticBezierLineRef (Line2 & setPoints).
  // LineMaterial (Line2.material) exposes opacity directly — no cast needed.
  const lineRef = useRef<QuadraticBezierLineRef>(null);
  useFrame(({ clock }) => {
    const mat = lineRef.current?.material;
    if (mat) mat.opacity = 0.35 + (Math.sin(clock.getElapsedTime() * 1.6) + 1) * 0.25;
  });
  if (!target) return null;
  const end: [number, number, number] = [target[0], 0.55, target[2]];
  const mid: [number, number, number] = [target[0] * 0.45, 2.6, target[2] * 0.45];
  return (
    <QuadraticBezierLine
      ref={lineRef}
      start={[0, 0.4, 0]}
      mid={mid}
      end={end}
      color={spec.color}
      lineWidth={2.2}
      transparent
      opacity={0.6}
    />
  );
}

/** 生年四化：自中宫（生辰）飞渡到四化星所在宫的光束 */
export function SihuaBeams({ chart, visible }: { chart: ZiweiChart; visible: boolean }) {
  const beams = useMemo(() => findMutagenPalaces(chart), [chart]);
  if (!visible) return null;
  return (
    <group>
      {beams.map((spec) => (
        <Beam key={`${spec.branch}-${spec.mutagen}`} spec={spec} />
      ))}
    </group>
  );
}
