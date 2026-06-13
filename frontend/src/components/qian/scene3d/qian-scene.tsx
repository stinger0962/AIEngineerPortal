"use client";
import { Suspense, useState, useEffect, useRef } from "react";
import { Canvas } from "@react-three/fiber";
import { PerformanceMonitor } from "@react-three/drei";
import { SignCylinder } from "./sign-cylinder";

export type QianSceneProps = { shaking: boolean; drawn: boolean; onRenderError?: () => void };

export default function QianScene({ shaking, drawn, onRenderError }: QianSceneProps) {
  const [q, setQ] = useState<"high" | "low">("high");
  const disposed = useRef(false);
  useEffect(() => () => void (disposed.current = true), []);
  return (
    <Canvas
      dpr={q === "high" ? [1, 1.75] : 1}
      camera={{ position: [0, 1.6, 6], fov: 42 }}
      style={{ background: "#140e08" }}
      onCreated={({ gl }) => {
        if (gl.getContext().isContextLost()) onRenderError?.();
        gl.domElement.addEventListener("webglcontextlost", () => { if (!disposed.current) onRenderError?.(); }, { once: true });
      }}
    >
      <PerformanceMonitor onDecline={() => setQ("low")}>
        <color attach="background" args={["#140e08"]} />
        <fog attach="fog" args={["#140e08", 9, 22]} />
        <ambientLight intensity={0.5} color="#f0d9a8" />
        <directionalLight position={[3, 6, 4]} intensity={0.8} color="#ffcf8a" />
        <pointLight position={[0, 2, 3]} intensity={0.6} color="#b9472f" />
        <Suspense fallback={null}>
          <SignCylinder shaking={shaking} drawn={drawn} />
        </Suspense>
      </PerformanceMonitor>
    </Canvas>
  );
}
