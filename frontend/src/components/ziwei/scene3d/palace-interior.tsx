"use client";

import { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Billboard, Text } from "@react-three/drei";
import * as THREE from "three";
import type { ZiweiPalace, ZiweiStar } from "@/lib/ziwei/types";
import { MUTAGEN_COLORS, branchPosition } from "./layout";
import { ZIWEI_FONT_URL, ZIWEI_GLYPHS } from "./glyphs";

function StarTablet({ star, major }: { star: ZiweiStar; major: boolean }) {
  const mutagenColor = star.mutagen ? MUTAGEN_COLORS[star.mutagen] : undefined;
  const w = major ? 0.78 : 0.6;
  const h = major ? 1.16 : 0.92;
  return (
    <Billboard>
      {/* 注册 onClick 让殿牌成为命中目标——否则点殿牌会被当成 pointerMissed 弹回总览 */}
      <mesh onClick={(e) => e.stopPropagation()}>
        <planeGeometry args={[w, h]} />
        <meshStandardMaterial
          color="#160b38"
          emissive={mutagenColor ?? "#8b5cf6"}
          emissiveIntensity={major ? 0.5 : 0.3}
          transparent
          opacity={0.92}
          side={THREE.DoubleSide}
        />
      </mesh>
      <Text
        font={ZIWEI_FONT_URL}
        characters={ZIWEI_GLYPHS}
        fontSize={major ? 0.27 : 0.2}
        color={major ? "#ffe9c4" : "#d8c8ff"}
        anchorX="center"
        anchorY="middle"
        position={[0, 0.12, 0.01]}
      >
        {star.name}
      </Text>
      <Text
        font={ZIWEI_FONT_URL}
        characters={ZIWEI_GLYPHS}
        fontSize={0.16}
        color="#9d8bd6"
        anchorX="center"
        anchorY="middle"
        position={[0, -0.24, 0.01]}
      >
        {[star.brightness, star.mutagen ? `化${star.mutagen}` : ""].filter(Boolean).join(" · ") || "—"}
      </Text>
    </Billboard>
  );
}

/** 选中宫位的内景：全部星曜（含杂曜）化作环形殿牌绕宫心旋转 */
export function PalaceInterior({ palace }: { palace: ZiweiPalace }) {
  const center = branchPosition(palace.earthlyBranch);
  const ringRef = useRef<THREE.Group>(null);
  const stars: Array<{ star: ZiweiStar; major: boolean }> = [
    ...palace.majorStars.map((star) => ({ star, major: true })),
    ...palace.minorStars.map((star) => ({ star, major: false })),
    ...palace.adjectiveStars.map((star) => ({ star, major: false })),
  ];

  useFrame((_, delta) => {
    if (ringRef.current) ringRef.current.rotation.y += delta * 0.18;
  });

  if (!center || stars.length === 0) return null;
  // 半径封顶 2.1：飞入相机距宫心仅约 2.4-3.2，星多时环不能扫到相机后面；超出部分用上下错层吸收
  const radius = Math.max(1.15, Math.min(2.1, stars.length * 0.21));
  const staggered = stars.length > 10;

  return (
    <group position={[center[0], 1.05, center[2]]}>
      {/* 宫心光核 */}
      <mesh>
        <sphereGeometry args={[0.16, 20, 20]} />
        <meshStandardMaterial color="#fff7df" emissive="#fbbf24" emissiveIntensity={2.2} />
      </mesh>
      <group ref={ringRef}>
        {stars.map(({ star, major }, i) => {
          const angle = (i / stars.length) * Math.PI * 2;
          const y = staggered ? (i % 2 === 0 ? 0.25 : -0.25) : 0;
          return (
            <group key={star.name} position={[Math.cos(angle) * radius, y, Math.sin(angle) * radius]}>
              <StarTablet star={star} major={major} />
            </group>
          );
        })}
      </group>
    </group>
  );
}
