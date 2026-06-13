"use client";
import { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import type { Group } from "three";

export function SignCylinder({ shaking, drawn }: { shaking: boolean; drawn: boolean }) {
  const cup = useRef<Group>(null);
  const stick = useRef<Group>(null);
  const t = useRef(0);
  useFrame((_, dt) => {
    t.current += dt;
    if (cup.current) {
      const amp = shaking ? 0.18 : 0;
      cup.current.rotation.z = Math.sin(t.current * 18) * amp;
      cup.current.position.x = Math.sin(t.current * 22) * amp * 0.3;
    }
    if (stick.current) {
      const targetY = drawn ? 2.4 : 0.2;
      stick.current.position.y += (targetY - stick.current.position.y) * (1 - Math.exp(-6 * dt));
    }
  });
  return (
    <group>
      <group ref={cup}>
        <mesh position={[0, 0, 0]}>
          <cylinderGeometry args={[0.9, 1.0, 2.2, 32, 1, true]} />
          <meshStandardMaterial color="#7a3b1d" metalness={0.3} roughness={0.6} side={2} />
        </mesh>
        {Array.from({ length: 14 }).map((_, i) => (
          <mesh key={i} position={[Math.cos(i) * 0.4, 1.1, Math.sin(i) * 0.4]} rotation={[0, 0, (i % 5 - 2) * 0.04]}>
            <boxGeometry args={[0.06, 1.8, 0.06]} />
            <meshStandardMaterial color="#d9c6a0" roughness={0.7} />
          </mesh>
        ))}
      </group>
      <group ref={stick} position={[0, 0.2, 0.5]}>
        <mesh>
          <boxGeometry args={[0.1, 2.6, 0.1]} />
          <meshStandardMaterial color="#d6a84a" emissive="#b9472f" emissiveIntensity={drawn ? 0.35 : 0} metalness={0.4} roughness={0.4} />
        </mesh>
      </group>
    </group>
  );
}
