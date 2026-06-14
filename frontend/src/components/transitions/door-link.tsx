"use client";

import { useCallback, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { playDoorOpen } from "@/lib/sound/door";

// A navigation link that, on click, plays a 对开门 (double-leaf swing-open)
// transition in the target domain's colors — two lacquer leaves part outward,
// the domain's light spills through — then routes after ~1.25s. Reused by the
// homepage 屏风 panels and the 命理 landing doors. Honors prefers-reduced-motion
// (skips straight to navigation).

export type DoorTheme = {
  /** Giant character shown split across the two leaves (e.g. 玄/造/学/紫/灵). */
  char: string;
  /** Main accent for the light spilling through + char tint. */
  accent: string;
  /** Inner-panel gradient painted on each leaf. */
  innerBg: string;
};

const SWING_MS = 1100;
const NAVIGATE_MS = 1250;

export function DoorLink({
  href,
  theme,
  className,
  style,
  ariaLabel,
  children,
}: {
  href: string;
  theme: DoorTheme;
  className?: string;
  style?: React.CSSProperties;
  ariaLabel?: string;
  children: React.ReactNode;
}) {
  const router = useRouter();
  const [opening, setOpening] = useState(false);
  const busy = useRef(false);

  const onClick = useCallback(
    (e: React.MouseEvent) => {
      // Let modified clicks (new tab, etc.) behave normally.
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) return;
      e.preventDefault();
      if (busy.current) return;
      busy.current = true;

      const reduce =
        typeof window !== "undefined" &&
        window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

      if (reduce) {
        router.push(href);
        return;
      }
      playDoorOpen();
      setOpening(true);
      router.prefetch?.(href);
      window.setTimeout(() => router.push(href), NAVIGATE_MS);
    },
    [href, router],
  );

  return (
    <>
      <a href={href} onClick={onClick} className={className} style={style} aria-label={ariaLabel}>
        {children}
      </a>
      {opening && <DoorOverlay theme={theme} />}
    </>
  );
}

function leafFace(theme: DoorTheme, side: "left" | "right"): React.CSSProperties {
  return {
    position: "absolute",
    top: 0,
    [side]: 0,
    width: "50%",
    height: "100%",
    transformOrigin: `${side} center`,
    background:
      side === "left"
        ? "linear-gradient(120deg,#3a1a0c,#1c0d06)"
        : "linear-gradient(240deg,#3a1a0c,#1c0d06)",
    boxShadow:
      side === "left"
        ? "inset -2px 0 0 rgba(202,164,74,.4)"
        : "inset 2px 0 0 rgba(202,164,74,.4)",
    overflow: "hidden",
    animation: `${side === "left" ? "door-swing-l" : "door-swing-r"} ${SWING_MS}ms cubic-bezier(.6,.02,.2,1) forwards`,
  };
}

function DoorOverlay({ theme }: { theme: DoorTheme }) {
  return (
    <div
      aria-hidden="true"
      style={{ position: "fixed", inset: 0, zIndex: 80, perspective: "1600px", overflow: "hidden" }}
    >
      <style>{`
        @keyframes door-swing-l { from { transform: rotateY(0); } to { transform: rotateY(-110deg); } }
        @keyframes door-swing-r { from { transform: rotateY(0); } to { transform: rotateY(110deg); } }
        @keyframes door-glow-in { from { opacity: 0; } to { opacity: 1; } }
      `}</style>

      {/* light spilling from behind the doors */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: `radial-gradient(80% 70% at 50% 50%, ${theme.accent}66, #050308 72%)`,
          animation: "door-glow-in 600ms ease forwards",
        }}
      />

      {/* left leaf */}
      <div style={leafFace(theme, "left")}>
        <div style={{ position: "absolute", inset: 9, borderRadius: 8, border: "1px solid rgba(202,164,74,.35)", background: theme.innerBg }} />
        <div style={{ position: "absolute", top: "50%", right: "-22%", transform: "translateY(-50%)", fontSize: "min(64vh,520px)", lineHeight: 0.7, color: theme.accent, opacity: 0.2, fontFamily: "'Songti SC','Noto Serif CJK SC','SimSun',serif" }}>
          {theme.char}
        </div>
      </div>

      {/* right leaf */}
      <div style={leafFace(theme, "right")}>
        <div style={{ position: "absolute", inset: 9, borderRadius: 8, border: "1px solid rgba(202,164,74,.35)", background: theme.innerBg }} />
        <div style={{ position: "absolute", top: "50%", left: "-22%", transform: "translateY(-50%)", fontSize: "min(64vh,520px)", lineHeight: 0.7, color: theme.accent, opacity: 0.2, fontFamily: "'Songti SC','Noto Serif CJK SC','SimSun',serif" }}>
          {theme.char}
        </div>
      </div>
    </div>
  );
}
