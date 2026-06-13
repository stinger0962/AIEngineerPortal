"use client";
import { useRef, useMemo } from "react";
import { useFrame } from "@react-three/fiber";
import type { Group, Mesh, PointLight } from "three";
import { DoubleSide } from "three";

// Seeded pseudo-random helpers (no Math.random at module scope)
function seededRadius(i: number) {
  return 0.06 + ((i * 37) % 26) / 26 * 0.42; // 0.06 – 0.48 (fits inside cup r=0.7)
}
function seededAngle(i: number) {
  return (i * 137.508) % 360; // golden-angle packing
}
function seededTilt(i: number) {
  return ((i * 71) % 14) / 14 * 0.12 - 0.06; // –0.06 … +0.06 rad
}

// Cup geometry constants
// Cup: cylinderGeometry args=[0.7, 0.78, 1.5, 48, 1, true]
// Cup bottom at y = -0.75, top rim at y = +0.75
// Cup center is at group y=0, so rim is at world y=0.75 (when group at y=0)
const CUP_RIM_Y = 0.75;      // local y of the rim top
const CUP_BOTTOM_Y = -0.75;  // local y of the bottom

const STICK_COUNT = 18;
// Sticks: height 1.3, center at y so tops are at CUP_RIM_Y + 0.2~0.4 above
// stick center y: top = center + h/2 = center + 0.65 = 0.75 + 0.25 = 1.0 → center = 0.35
// i.e. stick center at roughly 0.3 (a bit inside cup, tips poke out 0.2-0.4)
const STICK_H = 1.3;
const STICK_CENTER_Y = 0.30; // center of bundle sticks (top = 0.30+0.65=0.95, just above rim)

export function SignCylinder({ shaking, drawn }: { shaking: boolean; drawn: boolean }) {
  const cupRef = useRef<Group>(null);
  const sticksRef = useRef<Group>(null);
  const drawnRef = useRef<Group>(null);
  const tipLightRef = useRef<PointLight>(null);

  // Pre-compute stick positions/rotations from index (stable, no random)
  const stickData = useMemo(
    () =>
      Array.from({ length: STICK_COUNT }, (_, i) => {
        const r = seededRadius(i);
        const angleDeg = seededAngle(i);
        const angleRad = (angleDeg * Math.PI) / 180;
        const tilt = seededTilt(i);
        return {
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
        cupRef.current.rotation.z = Math.sin(t * 22) * 0.14;
        cupRef.current.rotation.x = Math.sin(t * 16) * 0.05;
        cupRef.current.position.x = Math.sin(t * 26) * 0.04;
        cupRef.current.position.y += (0 - cupRef.current.position.y) * (1 - Math.exp(-8 * dt));
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
      const k = 1 - Math.exp(-4 * dt);
      // When drawn: rise so stick center is at y≈1.8 (top at 1.8+1.1=2.9, well above rim at 0.75)
      // When not drawn: hidden low among bundle, center y≈0 (top at 1.1, just at rim, mostly inside)
      const targetY = drawn ? 1.8 : 0.0;
      const targetRZ = drawn ? 0.18 : 0;
      const targetEI = drawn ? 1.1 : 0;
      drawnRef.current.position.y += (targetY - drawnRef.current.position.y) * k;
      drawnRef.current.rotation.z += (targetRZ - drawnRef.current.rotation.z) * k;
      drawnRef.current.userData.targetEmissive = targetEI;
    }

    // update drawn stick mesh emissiveIntensity
    if (drawnRef.current) {
      drawnRef.current.traverse((child) => {
        if ((child as Mesh).isMesh) {
          const mat = (child as Mesh).material as unknown as THREE_MeshStandardMaterial;
          if (mat && typeof mat.emissiveIntensity === "number") {
            const target = drawnRef.current?.userData.targetEmissive ?? 0;
            mat.emissiveIntensity += (target - mat.emissiveIntensity) * (1 - Math.exp(-4 * dt));
          }
        }
      });
    }

    // update tip point light intensity
    if (tipLightRef.current) {
      const targetIntensity = drawn ? 1.4 : 0;
      tipLightRef.current.intensity += (targetIntensity - tipLightRef.current.intensity) * (1 - Math.exp(-4 * dt));
    }
  });

  return (
    // Cup group positioned so the cup occupies lower portion of frame.
    // Cup center at y=-0.3 → rim at y=0.45, plenty of headroom above
    <group position={[0, -0.3, 0]}>
      {/* Altar plane */}
      <mesh rotation-x={-Math.PI / 2} position-y={-1.1} receiveShadow>
        <planeGeometry args={[16, 16]} />
        <meshStandardMaterial color="#2a1810" roughness={0.9} metalness={0.05} />
      </mesh>

      {/* Cup group — shakes */}
      <group ref={cupRef}>
        {/* Lacquered cup wall (open cylinder, double-sided) */}
        <mesh>
          <cylinderGeometry args={[0.7, 0.78, 1.5, 48, 1, true]} />
          <meshStandardMaterial
            color="#5a2a14"
            metalness={0.35}
            roughness={0.5}
            side={DoubleSide}
          />
        </mesh>

        {/* Dark inner bottom cap — prevents seeing through */}
        <mesh position-y={CUP_BOTTOM_Y}>
          <circleGeometry args={[0.7, 48]} />
          <meshStandardMaterial color="#1e0c06" roughness={0.95} />
        </mesh>

        {/* Gold rim ring — torus at cup top, visible from above */}
        <mesh position-y={CUP_RIM_Y} rotation-x={Math.PI / 2}>
          <torusGeometry args={[0.72, 0.04, 16, 64]} />
          <meshStandardMaterial
            color="#d6a84a"
            emissive="#e7c372"
            emissiveIntensity={0.45}
            metalness={0.92}
            roughness={0.22}
          />
        </mesh>

        {/* Stick bundle — muted, short, rattle independently */}
        <group ref={sticksRef}>
          {stickData.map((s, i) => (
            <mesh
              key={i}
              position={[s.x, STICK_CENTER_Y, s.z]}
              rotation={[0, s.rotY, s.rotZ]}
            >
              <boxGeometry args={[0.045, STICK_H, 0.045]} />
              <meshStandardMaterial color="#cdb589" roughness={0.8} metalness={0.0} />
            </mesh>
          ))}
        </group>
      </group>

      {/* Drawn stick — rises out of cup on draw (outside cup group so it can move independently) */}
      <group ref={drawnRef} position={[0.08, 0.0, 0.12]}>
        {/* Main stick body — thicker, brighter gold */}
        <mesh>
          <boxGeometry args={[0.07, 2.2, 0.07]} />
          <meshStandardMaterial
            color="#f3e0a8"
            emissive="#e7c372"
            emissiveIntensity={0}
            metalness={0.55}
            roughness={0.28}
          />
        </mesh>
        {/* Tip accent */}
        <mesh position-y={1.12}>
          <boxGeometry args={[0.075, 0.1, 0.075]} />
          <meshStandardMaterial color="#b9975f" roughness={0.35} metalness={0.5} />
        </mesh>
        {/* Point light at stick tip — glows when drawn */}
        <pointLight
          ref={tipLightRef}
          position={[0, 1.2, 0]}
          color="#ffe6a8"
          intensity={0}
          distance={3}
          decay={2}
        />
      </group>
    </group>
  );
}

// Local type alias to avoid global THREE namespace conflicts
type THREE_MeshStandardMaterial = {
  emissiveIntensity: number;
  isMeshStandardMaterial?: boolean;
};
