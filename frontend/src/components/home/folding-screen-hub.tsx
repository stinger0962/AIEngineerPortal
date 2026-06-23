"use client";

import React, { useRef, useState } from "react";

import { DoorLink } from "@/components/transitions/door-link";

/**
 * 方寸 · 屏风 launcher (full-screen homepage).
 *
 * A Chinese folding screen (屏风) rendered edge-to-edge: a red-lacquer gold-inlay
 * frame holding three ink-wash panels (学 / 造 / 玄). Each panel is a single DOOR —
 * clicking it navigates directly to that domain's main page. No accordion, no
 * second-level menu. The sidebar is intentionally absent here (see AppShell): the
 * three doors ARE the navigation; the sidebar takes over once you enter a domain.
 */

// System CJK serif stack — NO Google Fonts (GFW blocks fonts.googleapis).
const SERIF = "'Songti SC','Noto Serif CJK SC','STSong','SimSun',serif";

type Domain = {
  key: "xue" | "zao" | "xuan";
  href: string;
  numeral: string; // 壹 / 贰 / 叁
  char: string; // giant watermark
  enLabel: string; // Grow / Distill / Oracle
  verticalName: string; // vertical realm name
  index: string; // sub-feature list (descriptive, not links)
  accent: string;
  accentLight: string;
  nameColor: string;
  bg: string; // panel base gradient
  glow: string; // hover radial wash
  backdrop: string; // opaque field revealed behind the doors (≈ destination bg)
  motif: React.ReactNode;
};

const DOMAINS: Domain[] = [
  {
    key: "xue",
    href: "/grow",
    numeral: "壹",
    char: "学",
    enLabel: "Grow",
    verticalName: "学 · 工程成长",
    index: "学 · 练 · 复习 · 面试 · 求职 · 한국어",
    accent: "#5fb3a3",
    accentLight: "#9fe0d2",
    nameColor: "#cdbd8e",
    bg: "linear-gradient(#0f1815,#0a110f)",
    glow: "radial-gradient(120% 90% at 50% 108%, rgba(95,179,163,.26), transparent 62%)",
    backdrop: "linear-gradient(135deg, #f3ead9, #eef3ec 58%, #f4eee4)",
    motif: (
      <svg width="42" height="42" viewBox="0 0 42 42" aria-hidden="true">
        <path
          d="M10 12h22M12 12v20c0 2 2 3 4 2l5-2 5 2c2 1 4 0 4-2V12M21 14v20"
          fill="none"
          stroke="#6fb6a6"
          strokeWidth="1.3"
          strokeLinecap="round"
        />
      </svg>
    ),
  },
  {
    key: "zao",
    href: "/toolkits",
    numeral: "贰",
    char: "造",
    enLabel: "Distill",
    verticalName: "蒸馏所 · 造",
    index: "炼 · 织 · 录 · 配",
    accent: "#e08a3c",
    accentLight: "#f0c082",
    nameColor: "#e7c372",
    bg: "linear-gradient(#1a120a,#100a06)",
    glow: "radial-gradient(120% 90% at 50% 108%, rgba(224,138,60,.26), transparent 62%)",
    backdrop: "radial-gradient(circle at top left, rgba(192,115,46,0.16), transparent 30%), linear-gradient(135deg, #f5ecdc, #efe2cd)",
    motif: (
      <svg width="42" height="46" viewBox="0 0 42 46" aria-hidden="true">
        <path
          d="M17 9h8M18 9c0 4-7 8-7 16a10 10 0 0020 0c0-8-7-12-7-16"
          fill="none"
          stroke="#e3a05c"
          strokeWidth="1.3"
          strokeLinecap="round"
        />
        <path d="M21 23c-3 2-3 6 0 8 3-2 3-6 0-8" fill="none" stroke="#f0c082" strokeWidth="1.2" />
      </svg>
    ),
  },
  {
    key: "xuan",
    href: "/xuan",
    numeral: "叁",
    char: "玄",
    enLabel: "Oracle",
    verticalName: "命理 · 玄",
    index: "紫微斗数 · 灵签",
    accent: "#9a7bf0",
    accentLight: "#bcaaf0",
    nameColor: "#cdbfff",
    bg: "linear-gradient(#100c1c,#0a0814)",
    glow: "radial-gradient(120% 90% at 50% 108%, rgba(154,123,240,.28), transparent 62%)",
    backdrop: "radial-gradient(130% 95% at 50% -6%, #1a1330, #0c0a18 55%)",
    motif: (
      <svg width="48" height="44" viewBox="0 0 48 44" aria-hidden="true">
        <g fill="#c9b6ff">
          <circle cx="10" cy="12" r="1.7" />
          <circle cx="20" cy="8" r="1.7" />
          <circle cx="29" cy="14" r="1.7" />
          <circle cx="38" cy="10" r="1.7" />
          <circle cx="41" cy="20" r="1.7" />
          <circle cx="34" cy="27" r="1.7" />
          <circle cx="25" cy="26" r="1.7" />
        </g>
        <path d="M10 12l10-4 9 6 9-4 3 10-7 7-9-1z" fill="none" stroke="#9a7bf0" strokeWidth="1" opacity=".6" />
      </svg>
    ),
  },
];

function DomainDoor({ domain }: { domain: Domain }) {
  return (
    <DoorLink
      href={domain.href}
      theme={{ char: domain.char, accent: domain.accent, innerBg: domain.bg, backdrop: domain.backdrop }}
      className="screen-door"
      ariaLabel={`${domain.verticalName} · 入口`}
      style={
        {
          "--accent": domain.accent,
          "--accent-light": domain.accentLight,
          position: "relative",
          display: "block",
          flex: 1,
          alignSelf: "stretch",
          minHeight: 0,
          overflow: "hidden",
          borderRadius: 12,
          border: "1px solid #2c2417",
          background: domain.bg,
          textDecoration: "none",
          fontFamily: SERIF,
        } as React.CSSProperties
      }
    >
      {/* hover wash from below */}
      <span
        className="screen-door-glow"
        aria-hidden="true"
        style={{ position: "absolute", inset: 0, background: domain.glow, opacity: 0, transition: "opacity .4s ease" }}
      />

      {/* giant watermark char — identical placement for all three */}
      <span
        aria-hidden="true"
        className="screen-door-char"
        style={{
          position: "absolute",
          left: "50%",
          bottom: "8%",
          transform: "translateX(-50%)",
          fontSize: "min(36vh, 360px)",
          lineHeight: 0.78,
          fontWeight: 500,
          color: domain.accent,
          opacity: 0.17,
          transition: "opacity .4s ease",
          pointerEvents: "none",
        }}
      >
        {domain.char}
      </span>

      {/* base mist */}
      <span
        aria-hidden="true"
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          bottom: 0,
          height: "34%",
          background: "linear-gradient(transparent, rgba(0,0,0,.45))",
          pointerEvents: "none",
        }}
      />

      {/* motif — top-left, same coords every panel */}
      <span style={{ position: "absolute", top: 26, left: 24, opacity: 0.85, pointerEvents: "none" }}>
        {domain.motif}
      </span>

      {/* vertical realm name — directly below the motif */}
      <span
        style={{
          position: "absolute",
          top: 86,
          left: 26,
          writingMode: "vertical-rl",
          fontSize: "clamp(20px, 2.4vh, 26px)",
          letterSpacing: 8,
          color: domain.nameColor,
          fontFamily: SERIF,
          pointerEvents: "none",
        }}
      >
        {domain.verticalName}
      </span>

      {/* numeral + EN eyebrow, top-right */}
      <span
        aria-hidden="true"
        style={{
          position: "absolute",
          top: 26,
          right: 24,
          textAlign: "right",
          fontFamily: "system-ui",
          color: domain.accent,
          pointerEvents: "none",
        }}
      >
        <span style={{ fontFamily: SERIF, fontSize: 17, display: "block", color: domain.nameColor }}>{domain.numeral}</span>
        <span style={{ fontSize: 10.5, letterSpacing: 3, opacity: 0.85 }}>{domain.enLabel.toUpperCase()}</span>
      </span>

      {/* bottom: index line + entrance CTA */}
      <span
        style={{
          position: "absolute",
          left: 24,
          right: 22,
          bottom: 22,
          display: "flex",
          alignItems: "flex-end",
          justifyContent: "space-between",
          gap: 12,
        }}
      >
        <span style={{ display: "block" }}>
          <span style={{ display: "block", fontSize: 11.5, letterSpacing: 1, color: "rgba(255,255,255,.42)", fontFamily: "system-ui" }}>
            {domain.index}
          </span>
        </span>
        <span
          className="screen-door-cta"
          style={{
            flexShrink: 0,
            fontSize: 15,
            letterSpacing: 2,
            color: domain.accentLight,
            fontFamily: SERIF,
            transition: "transform .35s ease, opacity .35s ease",
            opacity: 0.78,
          }}
        >
          入口&nbsp;→
        </span>
      </span>
    </DoorLink>
  );
}

function GoldSeam() {
  return (
    <div aria-hidden="true" style={{ width: 22, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
      <div style={{ width: 1, height: "82%", background: "linear-gradient(transparent,rgba(214,168,74,.5),transparent)" }} />
    </div>
  );
}

export default function FoldingScreenHub() {
  const pagerRef = useRef<HTMLDivElement>(null);
  const [active, setActive] = useState(0);

  const onPagerScroll = () => {
    const el = pagerRef.current;
    if (!el) return;
    const idx = Math.round(el.scrollLeft / el.clientWidth);
    setActive((prev) => (prev === idx ? prev : idx));
  };

  return (
    <>
      <style>{`
        .screen-door { transition: border-color .4s ease, box-shadow .4s ease; }
        .screen-pager::-webkit-scrollbar { display: none; }
        .screen-door:hover, .screen-door:focus-visible {
          border-color: color-mix(in srgb, var(--accent) 55%, #2c2417);
          box-shadow: 0 0 0 1px color-mix(in srgb, var(--accent) 45%, transparent),
                      0 18px 50px -28px var(--accent);
          outline: none;
        }
        .screen-door:hover .screen-door-glow,
        .screen-door:focus-visible .screen-door-glow { opacity: 1; }
        .screen-door:hover .screen-door-char,
        .screen-door:focus-visible .screen-door-char { opacity: .3; }
        .screen-door:hover .screen-door-cta,
        .screen-door:focus-visible .screen-door-cta { opacity: 1; transform: translateX(4px); }
        @media (prefers-reduced-motion: reduce) {
          .screen-door, .screen-door-glow, .screen-door-char, .screen-door-cta { transition: none !important; }
        }
      `}</style>

      {/* Full-bleed dark "room" the screen stands in */}
      <div
        style={{
          height: "100dvh",
          minHeight: "100dvh",
          width: "100%",
          display: "flex",
          flexDirection: "column",
          background: "radial-gradient(135% 100% at 50% -8%, #2c180c 0%, #160d07 42%, #0b0806 100%)",
          fontFamily: SERIF,
        }}
      >
        {/* Masthead */}
        <header
          style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            padding: "clamp(18px, 3.2vh, 30px) clamp(20px, 4vw, 46px)",
          }}
        >
          <div
            aria-hidden="true"
            style={{
              width: 32,
              height: 32,
              borderRadius: 6,
              background: "#b9472f",
              color: "#f3e6cf",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 19,
              fontFamily: SERIF,
              flexShrink: 0,
            }}
          >
            磊
          </div>
          <div style={{ fontSize: 20, color: "#ecdfc6", letterSpacing: 4, fontFamily: SERIF }}>方寸</div>
          <div style={{ fontSize: 11.5, color: "#9c8456", letterSpacing: 2, fontFamily: "system-ui", marginTop: 4 }}>
            三域门户
          </div>
          <div
            aria-hidden="true"
            style={{ marginLeft: "auto", fontSize: 12, color: "#9c8456", letterSpacing: 3, fontFamily: SERIF }}
          >
            学 · 造 · 玄
          </div>
        </header>

        {/* The folding screen — lacquer frame fills the rest of the viewport */}
        <main
          style={{
            flex: 1,
            minHeight: 0,
            display: "flex",
            flexDirection: "column",
            padding: "0 clamp(14px, 3vw, 40px) clamp(16px, 3.2vh, 38px)",
          }}
        >
          <div
            style={{
              flex: 1,
              minHeight: 0,
              display: "flex",
              padding: 13,
              borderRadius: 20,
              background: "linear-gradient(135deg,#3a1a0c,#1c0d06)",
              boxShadow:
                "inset 0 0 0 2px rgba(202,164,74,.55), inset 0 0 0 11px #190b05, inset 0 0 0 12px rgba(202,164,74,.35)",
            }}
          >
            {/* Desktop: three doors side by side */}
            <div className="hidden lg:flex" style={{ flex: 1, minWidth: 0 }}>
              {DOMAINS.map((domain, i) => (
                <React.Fragment key={domain.key}>
                  {i > 0 && <GoldSeam />}
                  <DomainDoor domain={domain} />
                </React.Fragment>
              ))}
            </div>

            {/* Mobile: full-screen swipeable pager — one 屏风 per page */}
            <div className="flex flex-col lg:hidden" style={{ flex: 1, minHeight: 0 }}>
              {/* ==——  position indicator */}
              <div style={{ display: "flex", justifyContent: "center", gap: 7, padding: "2px 0 11px", flexShrink: 0 }}>
                {DOMAINS.map((domain, i) => (
                  <span
                    key={domain.key}
                    aria-hidden="true"
                    style={{
                      height: 3,
                      borderRadius: 2,
                      width: i === active ? 26 : 13,
                      background: i === active ? domain.accent : "rgba(255,255,255,.22)",
                      transition: "width .3s ease, background .3s ease",
                    }}
                  />
                ))}
              </div>

              {/* swipe track (native scroll-snap, no JS lib) */}
              <div
                ref={pagerRef}
                onScroll={onPagerScroll}
                className="screen-pager"
                style={{
                  flex: 1,
                  minHeight: 0,
                  display: "flex",
                  overflowX: "auto",
                  overflowY: "hidden",
                  scrollSnapType: "x mandatory",
                  scrollbarWidth: "none",
                  WebkitOverflowScrolling: "touch",
                }}
              >
                {DOMAINS.map((domain) => (
                  <div
                    key={domain.key}
                    style={{ flex: "0 0 100%", minWidth: 0, display: "flex", scrollSnapAlign: "center" }}
                  >
                    <DomainDoor domain={domain} />
                  </div>
                ))}
              </div>
            </div>
          </div>
        </main>
      </div>
    </>
  );
}
