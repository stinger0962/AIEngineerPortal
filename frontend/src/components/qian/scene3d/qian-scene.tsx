"use client";
import { Suspense, useState, useEffect, useRef, useMemo } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { PerformanceMonitor } from "@react-three/drei";
import { EffectComposer, Bloom } from "@react-three/postprocessing";
import { SignCylinder } from "./sign-cylinder";

// ---------- Camera push-in on draw ----------
function CameraController({ drawn }: { drawn: boolean }) {
  const camera = useThree((s) => s.camera);
  useFrame((_, dt) => {
    const k = 1 - Math.exp(-3 * dt);
    const targetZ = drawn ? 4.6 : 6;
    const targetY = drawn ? 1.1 : 1.4;
    camera.position.z += (targetZ - camera.position.z) * k;
    camera.position.y += (targetY - camera.position.y) * k;
  });
  return null;
}

// ---------- Incense smoke ----------
const SMOKE_COUNT = 14;

// Seeded offsets — stable, no Math.random at module scope
function smokeX(i: number) {
  return ((i * 41) % 20) / 20 * 0.6 - 0.3; // –0.3 … +0.3
}
function smokePhase(i: number) {
  return ((i * 67) % 100) / 100; // 0..1 phase offset
}
function smokeXOffset(i: number) {
  return ((i * 29) % 20) / 20 * 0.4 - 0.2; // base x sway column
}

function Smoke() {
  // Each particle: [x0, yPhase, xSway, speed]
  const particles = useMemo(
    () =>
      Array.from({ length: SMOKE_COUNT }, (_, i) => ({
        x0: smokeX(i),
        phase: smokePhase(i),
        xBase: smokeXOffset(i),
        speed: 0.28 + ((i * 53) % 20) / 20 * 0.22, // 0.28–0.50 u/s
      })),
    []
  );

  const meshRefs = useRef<(import("three").Mesh | null)[]>([]);

  useFrame((state) => {
    const t = state.clock.elapsedTime;
    particles.forEach((p, i) => {
      const mesh = meshRefs.current[i];
      if (!mesh) return;
      // life cycles 0→1 based on phase
      const life = ((t * p.speed + p.phase) % 1 + 1) % 1; // 0→1
      const y = -1.0 + life * 4.5; // rises from -1.0 to 3.5
      const x = p.x0 + Math.sin(t * 1.2 + p.phase * Math.PI * 2) * 0.12;
      const opacity = life < 0.15
        ? life / 0.15 * 0.06
        : life > 0.75
        ? (1 - (life - 0.75) / 0.25) * 0.06
        : 0.06;
      mesh.position.set(x, y, -0.3);
      const mat = mesh.material as import("three").MeshBasicMaterial;
      mat.opacity = opacity;
      mesh.scale.setScalar(1 + life * 1.5); // expand as it rises
    });
  });

  return (
    <group position={[0, 0, -0.8]}>
      {particles.map((_, i) => (
        <mesh
          key={i}
          ref={(el) => { meshRefs.current[i] = el; }}
          position={[smokeX(i), -1.0 + smokePhase(i) * 4.5, -0.3]}
        >
          <planeGeometry args={[0.18, 0.5]} />
          <meshBasicMaterial
            color="#e7c372"
            transparent
            opacity={0.04}
            depthWrite={false}
          />
        </mesh>
      ))}
    </group>
  );
}

// ---------- Effects (mirrors ziwei effects.tsx pattern) ----------
function SceneEffects({ quality }: { quality: "high" | "low" }) {
  if (quality === "low") return null;
  return (
    <EffectComposer>
      <Bloom luminanceThreshold={0.32} luminanceSmoothing={0.82} intensity={0.85} mipmapBlur />
    </EffectComposer>
  );
}

// ---------- Props contract (MUST NOT change) ----------
export type QianSceneProps = { shaking: boolean; drawn: boolean; onRenderError?: () => void };

export default function QianScene({ shaking, drawn, onRenderError }: QianSceneProps) {
  const [q, setQ] = useState<"high" | "low">("high");
  const disposed = useRef(false);
  useEffect(() => () => void (disposed.current = true), []);

  return (
    <Canvas
      dpr={q === "high" ? [1, 1.75] : 1}
      camera={{ position: [0, 1.4, 6], fov: 42 }}
      style={{ background: "#140e08" }}
      onCreated={({ gl }) => {
        if (gl.getContext().isContextLost()) onRenderError?.();
        gl.domElement.addEventListener(
          "webglcontextlost",
          () => { if (!disposed.current) onRenderError?.(); },
          { once: true }
        );
      }}
    >
      <PerformanceMonitor onDecline={() => setQ("low")}>
        <color attach="background" args={["#140e08"]} />
        <fog attach="fog" args={["#140e08", 7, 20]} />

        {/* Warm temple lighting */}
        <ambientLight intensity={0.45} color="#f0d9a8" />
        <directionalLight position={[3, 6, 4]} intensity={0.9} color="#ffcf8a" castShadow />
        <pointLight position={[0, 0.5, 2]} intensity={0.7} color="#b9472f" />
        <spotLight
          position={[0, 5, 1]}
          angle={0.35}
          penumbra={0.6}
          intensity={0.5}
          color="#ffcf8a"
          target-position={[0, 0, 0]}
        />

        <Suspense fallback={null}>
          <SignCylinder shaking={shaking} drawn={drawn} />
          {q === "high" && <Smoke />}
        </Suspense>

        <CameraController drawn={drawn} />
        <SceneEffects quality={q} />
      </PerformanceMonitor>
    </Canvas>
  );
}
