"use client";
import { useRef, useMemo } from "react";
import { useFrame } from "@react-three/fiber";
import type { Group, Mesh } from "three";
import { DoubleSide } from "three";

// Seeded pseudo-random helpers (no Math.random at module scope)
function seededHeight(i: number) {
  return 1.5 + ((i * 53) % 40) / 40 * 0.5; // 1.5 – 2.0
}
function seededRadius(i: number) {
  return 0.08 + ((i * 37) % 26) / 26 * 0.47; // 0.08 – 0.55
}
function seededAngle(i: number) {
  return (i * 137.508) % 360; // golden-angle packing
}
function seededTilt(i: number) {
  return ((i * 71) % 14) / 14 * 0.14 - 0.07; // –0.07 … +0.07 rad
}

const STICK_COUNT = 26;

export function SignCylinder({ shaking, drawn }: { shaking: boolean; drawn: boolean }) {
  const cupRef = useRef<Group>(null);
  const sticksRef = useRef<Group>(null);
  const drawnRef = useRef<Group>(null);
  const bottomCapRef = useRef<Mesh>(null);

  // Pre-compute stick positions/rotations from index (stable, no random)
  const stickData = useMemo(
    () =>
      Array.from({ length: STICK_COUNT }, (_, i) => {
        const h = seededHeight(i);
        const r = seededRadius(i);
        const angleDeg = seededAngle(i);
        const angleRad = (angleDeg * Math.PI) / 180;
        const tilt = seededTilt(i);
        return {
          h,
          x: Math.cos(angleRad) * r,
          z: Math.sin(angleRad) * r,
          rotZ: tilt,
          rotY: angleRad,
        };
      }),
    []
  );

  useFrame((state, dt) => {
    const t = state.clock.elapsedTime;

    // --- cup shake ---
    if (cupRef.current) {
      if (shaking) {
        cupRef.current.rotation.z = Math.sin(t * 22) * 0.16;
        cupRef.current.rotation.x = Math.sin(t * 17) * 0.06;
        cupRef.current.position.x = Math.sin(t * 26) * 0.05;
        cupRef.current.position.y = Math.abs(Math.sin(t * 30)) * 0.04;
      } else {
        const k = 1 - Math.exp(-6 * dt);
        cupRef.current.rotation.z += (0 - cupRef.current.rotation.z) * k;
        cupRef.current.rotation.x += (0 - cupRef.current.rotation.x) * k;
        cupRef.current.position.x += (0 - cupRef.current.position.x) * k;
        cupRef.current.position.y += (0 - cupRef.current.position.y) * k;
      }
    }

    // --- sticks rattle ---
    if (sticksRef.current) {
      if (shaking) {
        sticksRef.current.rotation.z = Math.sin(t * 24) * 0.05;
        sticksRef.current.rotation.x = Math.sin(t * 19) * 0.03;
      } else {
        const k = 1 - Math.exp(-7 * dt);
        sticksRef.current.rotation.z += (0 - sticksRef.current.rotation.z) * k;
        sticksRef.current.rotation.x += (0 - sticksRef.current.rotation.x) * k;
      }
    }

    // --- drawn stick rise + tilt ---
    if (drawnRef.current) {
      const k = 1 - Math.exp(-5 * dt);
      const targetY = drawn ? 2.4 : 0.2;
      const targetRZ = drawn ? 0.22 : 0;
      const targetEI = drawn ? 0.8 : 0;
      drawnRef.current.position.y += (targetY - drawnRef.current.position.y) * k;
      drawnRef.current.rotation.z += (targetRZ - drawnRef.current.rotation.z) * k;
      // drive emissiveIntensity through userData
      drawnRef.current.userData.targetEmissive = targetEI;
    }
    // update drawn stick mesh emissiveIntensity
    if (drawnRef.current) {
      drawnRef.current.traverse((child) => {
        if ((child as Mesh).isMesh) {
          const mat = (child as Mesh).material as unknown as THREE_MeshStandardMaterial;
          if (mat && typeof mat.emissiveIntensity === "number") {
            const target = drawnRef.current?.userData.targetEmissive ?? 0;
            mat.emissiveIntensity += (target - mat.emissiveIntensity) * (1 - Math.exp(-5 * dt));
          }
        }
      });
    }
  });

  return (
    <group>
      {/* Altar plane */}
      <mesh rotation-x={-Math.PI / 2} position-y={-1.4} receiveShadow>
        <planeGeometry args={[14, 14]} />
        <meshStandardMaterial color="#2a1810" roughness={0.9} metalness={0.05} />
      </mesh>

      {/* Cup group — shakes */}
      <group ref={cupRef}>
        {/* Lacquered cup wall (open cylinder, double-sided) */}
        <mesh>
          <cylinderGeometry args={[0.95, 1.05, 2.2, 48, 1, true]} />
          <meshStandardMaterial
            color="#5a2a14"
            metalness={0.35}
            roughness={0.5}
            side={DoubleSide}
          />
        </mesh>

        {/* Dark inner bottom cap — prevents seeing through */}
        <mesh ref={bottomCapRef} position-y={-1.1}>
          <circleGeometry args={[0.95, 48]} />
          <meshStandardMaterial color="#2a1008" roughness={0.95} />
        </mesh>

        {/* Gold rim — torus ring at cup top */}
        <mesh position-y={1.11} rotation-x={Math.PI / 2}>
          <torusGeometry args={[0.97, 0.055, 16, 64]} />
          <meshStandardMaterial
            color="#d6a84a"
            emissive="#e7c372"
            emissiveIntensity={0.35}
            metalness={0.9}
            roughness={0.25}
          />
        </mesh>

        {/* Stick bundle — rattles independently */}
        <group ref={sticksRef}>
          {stickData.map((s, i) => (
            <mesh
              key={i}
              position={[s.x, s.h * 0.5 - 1.05, s.z]}
              rotation={[0, s.rotY, s.rotZ]}
            >
              <boxGeometry args={[0.05, s.h, 0.05]} />
              <meshStandardMaterial color="#d9c6a0" roughness={0.75} metalness={0.0} />
            </mesh>
          ))}
        </group>
      </group>

      {/* Drawn stick — rises out of cup on draw */}
      <group ref={drawnRef} position={[0.1, 0.2, 0.15]}>
        <mesh>
          <boxGeometry args={[0.08, 2.6, 0.08]} />
          <meshStandardMaterial
            color="#e7c372"
            emissive="#d6a84a"
            emissiveIntensity={0}
            metalness={0.55}
            roughness={0.3}
          />
        </mesh>
        {/* Tip accent — slightly darker */}
        <mesh position-y={1.35}>
          <boxGeometry args={[0.085, 0.12, 0.085]} />
          <meshStandardMaterial color="#b9975f" roughness={0.4} metalness={0.45} />
        </mesh>
      </group>
    </group>
  );
}

// Local type alias to avoid global THREE namespace conflicts
type THREE_MeshStandardMaterial = {
  emissiveIntensity: number;
  isMeshStandardMaterial?: boolean;
};
