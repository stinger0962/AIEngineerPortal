"use client";

import { useRef, useState } from "react";
import type { NodeKind } from "@/lib/korean/types";
import { KIND_THEME } from "@/lib/korean/theme";

type Glaze = "celadon" | "warm" | "clay";
const GLAZE_ACCENT: Record<Glaze, string> = {
  celadon: "var(--kr-reading)",
  warm: "var(--kr-drill)",
  clay: "var(--kr-scene)",
};

/* ---- eyebrow / section label, with a celadon brush dash ---- */
export function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.28em] text-[var(--celadon-700)]">
      <span className="inline-block h-1.5 w-5 rounded-full" style={{ background: "linear-gradient(90deg,var(--celadon-500),transparent)" }} />
      {children}
    </p>
  );
}

/* ---- star rating (antique gold) ---- */
function StarGlyph({ filled }: { filled: boolean }) {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" aria-hidden>
      <path
        d="M12 2.6l2.7 5.9 6.4.7-4.8 4.3 1.3 6.3L12 16.9 6.4 19.8l1.3-6.3L2.9 9.2l6.4-.7z"
        fill={filled ? "var(--kr-gold)" : "none"}
        stroke={filled ? "var(--kr-gold)" : "rgba(20,33,61,0.22)"}
        strokeWidth="1.4"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function Stars({ value, max = 3 }: { value: number; max?: number }) {
  return (
    <span className="inline-flex items-center gap-0.5" aria-label={`${value} of ${max} stars`}>
      {Array.from({ length: max }, (_, i) => (
        <StarGlyph key={i} filled={i < value} />
      ))}
    </span>
  );
}

/* ---- circular seal stamp for a node kind ---- */
export function KindSeal({ kind, size = 44 }: { kind: NodeKind; size?: number }) {
  const t = KIND_THEME[kind];
  return (
    <span
      className="font-kr-serif inline-flex items-center justify-center rounded-full"
      style={{
        width: size,
        height: size,
        fontSize: size * 0.45,
        color: t.accent,
        background: t.soft,
        border: `1.5px solid ${t.accent}`,
        boxShadow: "0 1px 0 rgba(255,255,255,0.7) inset",
      }}
    >
      {t.seal}
    </span>
  );
}

/* ---- primary CTA: glaze + shine sweep on hover ---- */
export function PrimaryButton({
  children,
  onClick,
  tone = "celadon",
  disabled,
  type = "button",
}: {
  children: React.ReactNode;
  onClick?: () => void;
  tone?: "celadon" | "gold";
  disabled?: boolean;
  type?: "button" | "submit";
}) {
  const grad =
    tone === "gold"
      ? "linear-gradient(180deg,#dcb85f,#c79a3a)"
      : "linear-gradient(180deg,var(--celadon-500),var(--celadon-600))";
  const shadow = tone === "gold" ? "0 16px 30px -12px rgba(199,154,58,0.7)" : "0 16px 30px -12px rgba(47,111,100,0.7)";
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className="k-press k-shine-sweep inline-flex items-center justify-center gap-2 rounded-2xl px-7 py-3 text-sm font-bold text-white transition-transform hover:-translate-y-0.5 disabled:opacity-50"
      style={{ background: grad, boxShadow: shadow }}
    >
      <span className="relative">{children}</span>
    </button>
  );
}

/* ---- glossy, colorful, springy speak tile: tap → pop + ripple + voice ---- */
export function SpeakTile({
  ko,
  sub,
  onSpeak,
  glaze = "celadon",
  accent,
  className = "",
  koClassName = "text-3xl",
}: {
  ko: string;
  sub?: string;
  onSpeak: () => void | Promise<void>;
  glaze?: Glaze;
  accent?: string;
  className?: string;
  koClassName?: string;
}) {
  const tint = accent ?? GLAZE_ACCENT[glaze];
  const [ripples, setRipples] = useState<number[]>([]);
  const [playing, setPlaying] = useState(false);
  const counter = useRef(0);

  const handle = async () => {
    const id = counter.current++;
    setRipples((r) => [...r, id]);
    window.setTimeout(() => setRipples((r) => r.filter((x) => x !== id)), 600);
    setPlaying(true);
    try {
      await onSpeak();
    } finally {
      window.setTimeout(() => setPlaying(false), 520);
    }
  };

  return (
    <button
      onClick={handle}
      className={`k-tile k-glaze-${glaze} group relative flex min-w-[84px] flex-col items-center justify-center gap-1.5 px-4 py-3.5 ${
        playing ? "k-poptile" : ""
      } ${className}`}
    >
      {ripples.map((id) => (
        <span
          key={id}
          className="pointer-events-none absolute left-1/2 top-1/2 -ml-7 -mt-7 h-14 w-14 rounded-full"
          style={{ background: tint, animation: "k-ripple 0.6s ease-out forwards" }}
        />
      ))}
      <svg
        viewBox="0 0 24 24"
        className="absolute right-2 top-2 h-3.5 w-3.5 transition-opacity"
        style={{ color: tint, opacity: playing ? 1 : 0.4 }}
        aria-hidden
      >
        <path d="M4 9v6h4l5 4V5L8 9H4z" fill="currentColor" />
        {playing && (
          <path d="M16 8c1.5 1.2 1.5 6.8 0 8M18.5 6c2.8 2 2.8 10 0 12" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
        )}
      </svg>
      <span className={`font-kr-serif relative leading-none text-ink ${koClassName}`}>{ko}</span>
      {sub && (
        <span className="font-kr relative rounded-full bg-white/70 px-2 py-0.5 text-[11px] font-medium text-ink/55">{sub}</span>
      )}
    </button>
  );
}
