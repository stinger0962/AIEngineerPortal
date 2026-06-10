"use client";

import { useEffect, useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import { Text } from "@react-three/drei";
import * as THREE from "three";
import type { ZiweiPalace } from "@/lib/ziwei/types";
import { CELL_W, CELL_D, PLATE_H, PLATE_EDGE, SOUL_EDGE, branchPosition } from "./layout";
import { ZIWEI_FONT_URL, ZIWEI_GLYPHS } from "./glyphs";
import { StarOrb } from "./star-orb";

export type PalacePlateProps = {
  palace: ZiweiPalace;
  isSoulPalace: boolean;
  dimmed: boolean;
  onSelect: (branch: string) => void;
};

export function PalacePlate({ palace, isSoulPalace, dimmed, onSelect }: PalacePlateProps) {
  const position = branchPosition(palace.earthlyBranch);
  const [hovered, setHovered] = useState(false);
  const hoveredRef = useRef(false);
  const matRef = useRef<THREE.MeshStandardMaterial>(null);

  // 悬停中卸载（如 webglcontextlost 回退）时恢复指针——onPointerOut 不会再触发
  useEffect(() => () => {
    if (hoveredRef.current) document.body.style.cursor = "auto";
  }, []);

  useFrame((_, delta) => {
    if (!matRef.current) return;
    // 1-exp(-k·dt)：帧率无关、且 t 恒在 (0,1)——裸 delta*6 在后台标签页恢复时会 >1 导致过冲闪烁
    const t = 1 - Math.exp(-6 * delta);
    const target = dimmed ? (hovered ? 0.12 : 0.04) : hovered ? 0.5 : isSoulPalace ? 0.3 : 0.16;
    matRef.current.emissiveIntensity = THREE.MathUtils.lerp(matRef.current.emissiveIntensity, target, t);
    const targetOpacity = dimmed ? 0.25 : 1;
    matRef.current.opacity = THREE.MathUtils.lerp(matRef.current.opacity, targetOpacity, t);
  });

  if (!position) return null;
  const edgeColor = isSoulPalace ? SOUL_EDGE : PLATE_EDGE;

  return (
    <group position={position}>
      {/* 殿板 */}
      <mesh
        onClick={(e) => {
          e.stopPropagation();
          onSelect(palace.earthlyBranch);
        }}
        onPointerOver={(e) => {
          e.stopPropagation();
          setHovered(true);
          hoveredRef.current = true;
          document.body.style.cursor = "pointer";
        }}
        onPointerOut={() => {
          setHovered(false);
          hoveredRef.current = false;
          document.body.style.cursor = "auto";
        }}
      >
        <boxGeometry args={[CELL_W - 0.22, PLATE_H, CELL_D - 0.22]} />
        <meshStandardMaterial
          ref={matRef}
          color="#1a1035"
          emissive={edgeColor}
          emissiveIntensity={0.16}
          transparent
          opacity={1}
          roughness={0.55}
          metalness={0.35}
        />
      </mesh>

      {/* 宫名（板面前缘） */}
      <Text
        font={ZIWEI_FONT_URL}
        characters={ZIWEI_GLYPHS}
        fontSize={0.34}
        color={dimmed ? "#4c3d77" : "#e9ddff"}
        anchorX="right"
        anchorY="bottom"
        position={[CELL_W / 2 - 0.32, PLATE_H / 2 + 0.012, CELL_D / 2 - 0.34]}
        rotation={[-Math.PI / 2, 0, 0]}
      >
        {palace.name}
        {palace.isBodyPalace ? " ·身" : ""}
      </Text>

      {/* 干支 + 大限（板面前缘左侧小字） */}
      <Text
        font={ZIWEI_FONT_URL}
        characters={ZIWEI_GLYPHS}
        fontSize={0.2}
        color={dimmed ? "#3c3060" : "#9d8bd6"}
        anchorX="left"
        anchorY="bottom"
        position={[-CELL_W / 2 + 0.32, PLATE_H / 2 + 0.012, CELL_D / 2 - 0.34]}
        rotation={[-Math.PI / 2, 0, 0]}
      >
        {`${palace.heavenlyStem}${palace.earthlyBranch} · ${palace.decadal.range[0]}-${palace.decadal.range[1]}`}
      </Text>

      {/* 星曜光球：主星排后、辅星排前 */}
      {palace.majorStars.map((star, i) => (
        <StarOrb
          key={star.name}
          star={star}
          major
          dimmed={dimmed}
          position={[(i - (palace.majorStars.length - 1) / 2) * 0.78, 0.46, -CELL_D / 2 + 1.0]}
        />
      ))}
      {/* 不截断：辅星可叠至 9-10 颗（昌曲/辅弼/火铃/空劫成对+禄存系），丢星会让四化光束指向无星之宫 */}
      {palace.minorStars.map((star, i) => {
        const perRow = 4;
        const row = Math.floor(i / perRow);
        const indexInRow = i % perRow;
        const rowCount = Math.min(palace.minorStars.length - row * perRow, perRow);
        return (
          <StarOrb
            key={star.name}
            star={star}
            major={false}
            dimmed={dimmed}
            position={[(indexInRow - (rowCount - 1) / 2) * 0.52, 0.4, -CELL_D / 2 + 1.78 + row * 0.5]}
          />
        );
      })}
    </group>
  );
}
