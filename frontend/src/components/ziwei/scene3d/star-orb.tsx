"use client";

import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Text } from "@react-three/drei";
import * as THREE from "three";
import type { ZiweiStar } from "@/lib/ziwei/types";
import { MUTAGEN_COLORS } from "./layout";
import { ZIWEI_FONT_URL, ZIWEI_GLYPHS } from "./glyphs";

export type StarOrbProps = {
  star: ZiweiStar;
  major: boolean;
  position: [number, number, number];
  dimmed: boolean;
};

export function StarOrb({ star, major, position, dimmed }: StarOrbProps) {
  const groupRef = useRef<THREE.Group>(null);
  const phase = useMemo(() => Math.random() * Math.PI * 2, []);
  const radius = major ? 0.17 : 0.1;
  const orbColor = major ? "#ffd9a0" : "#b9a8ef";
  const mutagenColor = star.mutagen ? MUTAGEN_COLORS[star.mutagen] : undefined;

  useFrame(({ clock }) => {
    if (!groupRef.current) return;
    groupRef.current.position.y = position[1] + Math.sin(clock.getElapsedTime() * 1.4 + phase) * 0.06;
  });

  return (
    <group ref={groupRef} position={position}>
      <mesh>
        <sphereGeometry args={[radius, 20, 20]} />
        <meshStandardMaterial
          color={orbColor}
          emissive={mutagenColor ?? orbColor}
          emissiveIntensity={dimmed ? 0.1 : major ? 1.6 : 0.9}
          transparent
          opacity={dimmed ? 0.3 : 1}
        />
      </mesh>
      {/* 四化光环 */}
      {mutagenColor ? (
        <mesh rotation={[-Math.PI / 2, 0, 0]}>
          <torusGeometry args={[radius + 0.07, 0.018, 10, 36]} />
          <meshBasicMaterial color={mutagenColor} transparent opacity={dimmed ? 0.15 : 0.9} />
        </mesh>
      ) : null}
      {/* 星名（含亮度），朝上贴板便于总览阅读 */}
      <Text
        font={ZIWEI_FONT_URL}
        characters={ZIWEI_GLYPHS}
        fontSize={major ? 0.24 : 0.17}
        color={dimmed ? "#4c3d77" : major ? "#ffe9c4" : "#c9b9ef"}
        anchorX="center"
        anchorY="top"
        position={[0, -radius - 0.08, 0]}
        rotation={[-Math.PI / 2, 0, 0]}
      >
        {star.brightness ? `${star.name}·${star.brightness}` : star.name}
      </Text>
    </group>
  );
}
