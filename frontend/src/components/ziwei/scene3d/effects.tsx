"use client";

import { Bloom, EffectComposer, Vignette } from "@react-three/postprocessing";

/** 低档位直接不渲染 Composer（省一条渲染管线） */
export function SceneEffects({ quality }: { quality: "high" | "low" }) {
  if (quality === "low") return null;
  return (
    <EffectComposer>
      <Bloom luminanceThreshold={0.35} luminanceSmoothing={0.85} intensity={0.9} mipmapBlur />
      <Vignette eskil={false} offset={0.18} darkness={0.85} />
    </EffectComposer>
  );
}
