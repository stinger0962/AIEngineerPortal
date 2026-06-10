"use client";

import { useEffect, useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Sparkles, Stars } from "@react-three/drei";
import * as THREE from "three";

/** 用 canvas 画一张径向渐变贴图作星云 sprite（免外部资源） */
function makeNebulaTexture(inner: string, outer: string): THREE.CanvasTexture {
  const size = 256;
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext("2d")!;
  const grad = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  grad.addColorStop(0, inner);
  grad.addColorStop(1, outer);
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, size, size);
  const texture = new THREE.CanvasTexture(canvas);
  texture.needsUpdate = true;
  return texture;
}

function Nebula({ position, scale, inner }: { position: [number, number, number]; scale: number; inner: string }) {
  const texture = useMemo(() => makeNebulaTexture(inner, "rgba(5,3,16,0)"), [inner]);
  useEffect(() => () => texture.dispose(), [texture]); // GPU 纹理随组件卸载释放
  const ref = useRef<THREE.Sprite>(null);
  useFrame(({ clock }) => {
    if (!ref.current) return;
    const t = clock.getElapsedTime();
    ref.current.position.x = position[0] + Math.sin(t * 0.05) * 1.2;
    ref.current.position.y = position[1] + Math.cos(t * 0.04) * 0.8;
  });
  return (
    <sprite ref={ref} position={position} scale={[scale, scale, 1]}>
      <spriteMaterial map={texture} transparent opacity={0.5} depthWrite={false} />
    </sprite>
  );
}

export function Starfield({ quality }: { quality: "high" | "low" }) {
  const starCount = quality === "high" ? 4500 : 2200;
  const sparkleCount = quality === "high" ? 90 : 40;
  return (
    <group>
      <Stars radius={60} depth={40} count={starCount} factor={3.2} saturation={0.4} fade speed={0.6} />
      <Sparkles count={sparkleCount} scale={[34, 18, 34]} size={2.4} speed={0.25} opacity={0.55} color="#c4b5fd" />
      <Nebula position={[-14, 6, -18]} scale={34} inner="rgba(124,58,237,0.32)" />
      <Nebula position={[16, 9, -22]} scale={40} inner="rgba(56,120,220,0.22)" />
      <Nebula position={[2, -7, -16]} scale={26} inner="rgba(190,80,200,0.16)" />
    </group>
  );
}
