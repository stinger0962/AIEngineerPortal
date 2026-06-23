"use client";

import { useRef, useState } from "react";
import type { NodeKind } from "@/lib/korean/types";
import { KIND_THEME } from "@/lib/korean/theme";

/* ---- eyebrow / section label (celadon, matches platform eyebrow pattern) ---- */
export function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-[var(--celadon-700)]">
      {children}
    </p>
  );
}

/* ---- star rating (antique gold) ---- */
function StarGlyph({ filled }: { filled: boolean }) {
  return (
    <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" aria-hidden>
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

/* ---- primary CTA: celadon glaze (or gold for boss claim) ---- */
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
      ? "linear-gradient(180deg,#d8b35a,#c79a3a)"
      : "linear-gradient(180deg,var(--celadon-500),var(--celadon-600))";
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className="k-press rounded-2xl px-6 py-2.5 text-sm font-semibold text-white shadow-[0_14px_30px_-12px_rgba(47,111,100,0.7)] disabled:opacity-50"
      style={{ background: grad }}
    >
      {children}
    </button>
  );
}

/* ---- tactile speak tile: tap → ripple + speaker pulse, plays Korean TTS ---- */
export function SpeakTile({
  ko,
  sub,
  onSpeak,
  accent = "var(--kr-reading)",
  className = "",
  koClassName = "text-2xl",
}: {
  ko: string;
  sub?: string;
  onSpeak: () => void | Promise<void>;
  accent?: string;
  className?: string;
  koClassName?: string;
}) {
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
      window.setTimeout(() => setPlaying(false), 480);
    }
  };

  return (
    <button
      onClick={handle}
      className={`k-card k-press group relative flex items-center gap-2 overflow-hidden rounded-2xl px-4 py-3 text-left ${className}`}
      style={{ borderColor: playing ? accent : undefined }}
    >
      {ripples.map((id) => (
        <span
          key={id}
          className="pointer-events-none absolute left-1/2 top-1/2 -ml-6 -mt-6 h-12 w-12 rounded-full"
          style={{ background: accent, animation: "k-ripple 0.6s ease-out forwards" }}
        />
      ))}
      <span className="relative flex items-baseline gap-1.5">
        <span className={`font-kr-serif leading-none text-ink ${koClassName}`}>{ko}</span>
        {sub && <span className="font-kr text-xs text-ink/45">{sub}</span>}
      </span>
      <svg
        viewBox="0 0 24 24"
        className="relative ml-auto h-4 w-4 shrink-0 transition-opacity"
        style={{ color: accent, opacity: playing ? 1 : 0.35 }}
        aria-hidden
      >
        <path d="M4 9v6h4l5 4V5L8 9H4z" fill="currentColor" />
        {playing && (
          <path d="M16 8c1.5 1.2 1.5 6.8 0 8M18.5 6c2.8 2 2.8 10 0 12" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
        )}
      </svg>
    </button>
  );
}
