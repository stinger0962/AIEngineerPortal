"use client";

import { useEffect, useRef } from "react";
import { CameraControls } from "@react-three/drei";
import type CameraControlsImpl from "camera-controls";
import { branchPosition } from "./layout";

const OVERVIEW_POS: [number, number, number] = [0, 12, 10.5];
const OVERVIEW_TARGET: [number, number, number] = [0, 0, 0];

export function useReducedMotion(): boolean {
  if (typeof window === "undefined") return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/** selectedBranch 变化时执行一镜到底运镜；用户拖拽随时可打断（CameraControls 原生支持） */
export function CameraRig({ selectedBranch, smoothTime = 0.45 }: { selectedBranch: string | null; smoothTime?: number }) {
  const controlsRef = useRef<CameraControlsImpl>(null);
  const reducedMotion = useReducedMotion();

  useEffect(() => {
    const controls = controlsRef.current;
    if (!controls) return;
    const transition = !reducedMotion;
    if (selectedBranch) {
      const target = branchPosition(selectedBranch);
      if (!target) return;
      void controls.setLookAt(
        target[0] * 1.08,
        3.4,
        target[2] * 1.08 + 2.8,
        target[0],
        0.7,
        target[2],
        transition,
      );
    } else {
      void controls.setLookAt(...OVERVIEW_POS, ...OVERVIEW_TARGET, transition);
    }
  }, [selectedBranch, reducedMotion]);

  return (
    <CameraControls
      ref={controlsRef}
      makeDefault
      minDistance={3}
      maxDistance={28}
      maxPolarAngle={Math.PI * 0.46}
      smoothTime={smoothTime}
    />
  );
}
