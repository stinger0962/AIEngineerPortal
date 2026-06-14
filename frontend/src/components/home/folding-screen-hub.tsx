"use client";

import React, { useState } from "react";
import Link from "next/link";

// ---------------------------------------------------------------------------
// Typography constant — system CJK serif, no web-font dependency
// ---------------------------------------------------------------------------
const SERIF = "'Songti SC','Noto Serif CJK SC','SimSun',serif";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
type Sub = { label: string; href: string; desc: string };

interface Domain {
  key: "xue" | "zao" | "xuan";
  numeral: string;
  char: string;
  nameCnVertical: string; // shown in vertical text (equal + sliver)
  titleCn: string;        // big heading when expanded
  enLabel: string;
  tagline: string;
  bgCollapsed: string;
  bgExpanded: string;
  accent: string;
  accentLight: string;
  nameColor: string;
  borderExpanded: string;
  motif: React.ReactNode;
  indexLabel: string;
  indexLine: string;
  subs: Sub[];
}

// ---------------------------------------------------------------------------
// Motifs (small ink-wash line art)
// ---------------------------------------------------------------------------
const MotifXue = (
  <svg width="40" height="40" viewBox="0 0 40 40" aria-hidden="true">
    <path
      d="M9 11h22M11 11v20c0 2 2 3 4 2l5-2 5 2c2 1 4 0 4-2V11M20 13v20"
      fill="none"
      stroke="#6fb6a6"
      strokeWidth="1.3"
      strokeLinecap="round"
    />
  </svg>
);

const MotifZao = (
  <svg width="40" height="44" viewBox="0 0 40 44" aria-hidden="true">
    <path
      d="M16 8h8M17 8c0 4-7 8-7 16a10 10 0 0020 0c0-8-7-12-7-16"
      fill="none"
      stroke="#e3a05c"
      strokeWidth="1.3"
      strokeLinecap="round"
    />
    <path
      d="M20 22c-3 2-3 6 0 8 3-2 3-6 0-8"
      fill="none"
      stroke="#f0c082"
      strokeWidth="1.2"
    />
  </svg>
);

const MotifXuan = (
  <svg width="46" height="44" viewBox="0 0 46 44" aria-hidden="true">
    <g fill="#c9b6ff">
      <circle cx="10" cy="12" r="1.6" />
      <circle cx="20" cy="8" r="1.6" />
      <circle cx="29" cy="14" r="1.6" />
      <circle cx="37" cy="10" r="1.6" />
      <circle cx="40" cy="20" r="1.6" />
      <circle cx="33" cy="27" r="1.6" />
      <circle cx="24" cy="26" r="1.6" />
    </g>
    <path
      d="M10 12l10-4 9 6 8-4 3 10-7 7-9-1z"
      fill="none"
      stroke="#9a7bf0"
      strokeWidth="1"
      opacity="0.6"
    />
  </svg>
);

// Cloud motif for 学 (equal state top-left)
const CloudMotif = (
  <svg
    width="34"
    height="20"
    viewBox="0 0 34 20"
    style={{ position: "absolute", top: 14, left: 16, opacity: 0.5 }}
    aria-hidden="true"
  >
    <path
      d="M2 14c4 0 4-6 9-6s5 6 10 4 5-8 11-4"
      fill="none"
      stroke="#5fb3a3"
      strokeWidth="1"
    />
  </svg>
);

// ---------------------------------------------------------------------------
// Domain data
// ---------------------------------------------------------------------------
const DOMAINS: Domain[] = [
  {
    key: "xue",
    numeral: "壹",
    char: "学",
    nameCnVertical: "学 · 工程成长",
    titleCn: "学 · 工程成长",
    enLabel: "Grow",
    tagline: "AI 工程成长 · 学练复习 · 面试求职",
    bgCollapsed: "linear-gradient(#0f1815,#0a110f)",
    bgExpanded:
      "radial-gradient(130% 80% at 80% 100%,rgba(95,179,163,.20),#08110e 60%)",
    accent: "#5fb3a3",
    accentLight: "#9fe0d2",
    nameColor: "#cdbd8e",
    borderExpanded: "rgba(95,179,163,.3)",
    motif: MotifXue,
    indexLabel: "壹 · Grow",
    indexLine: "学 练 复习 面试 求职",
    subs: [
      { label: "学域总览", href: "/grow", desc: "总览学习路径与进度" },
      { label: "Learn 学", href: "/learn", desc: "系统学习路径" },
      { label: "练 Practice", href: "/practice/python", desc: "动手练习" },
      { label: "复习 Review", href: "/review", desc: "间隔重复复习" },
      { label: "面试 Interview", href: "/interview", desc: "AI 模拟面试" },
      { label: "作品 Portfolio", href: "/projects", desc: "项目作品集" },
      { label: "简历 Resume", href: "/resume", desc: "简历生成与优化" },
      { label: "求职 Jobs", href: "/jobs/live", desc: "实时求职动态" },
      { label: "Copilot", href: "/copilot", desc: "AI 学习助手" },
    ],
  },
  {
    key: "zao",
    numeral: "贰",
    char: "造",
    nameCnVertical: "蒸馏所 · 造",
    titleCn: "蒸馏所 · 造",
    enLabel: "Distill",
    tagline: "内容蒸馏工具 · 炼织录配",
    bgCollapsed: "linear-gradient(#1a120a,#100a06)",
    bgExpanded:
      "radial-gradient(130% 80% at 80% 100%,rgba(224,138,60,.20),#140a06 60%)",
    accent: "#e08a3c",
    accentLight: "#f0c082",
    nameColor: "#e7c372",
    borderExpanded: "rgba(224,138,60,.3)",
    motif: MotifZao,
    indexLabel: "贰 · Distill",
    indexLine: "炼 织 录 配",
    subs: [
      { label: "蒸馏所", href: "/toolkits", desc: "工具套件总览" },
      { label: "炼 Forge", href: "/toolkits/podcast", desc: "播客精炼提取" },
      { label: "织 Loom", href: "/toolkits/summarize", desc: "长文摘要编织" },
      { label: "录 Scribe", href: "/toolkits/scribe", desc: "语音转录笔记" },
      { label: "配 Dub", href: "/toolkits/dub", desc: "AI 视频配音" },
    ],
  },
  {
    key: "xuan",
    numeral: "叁",
    char: "玄",
    nameCnVertical: "命理 · 玄",
    titleCn: "命理 · 玄",
    enLabel: "Oracle",
    tagline: "占卜与玄学 · 问一事，观天机",
    bgCollapsed: "linear-gradient(#100c1c,#0a0814)",
    bgExpanded:
      "radial-gradient(130% 80% at 80% 100%,rgba(154,123,240,.22),#0c0a18 60%)",
    accent: "#9a7bf0",
    accentLight: "#bcaaf0",
    nameColor: "#cdbfff",
    borderExpanded: "rgba(154,123,240,.3)",
    motif: MotifXuan,
    indexLabel: "叁 · Oracle",
    indexLine: "紫微斗数 · 灵签",
    subs: [
      {
        label: "紫微斗数",
        href: "/ziwei",
        desc: "3D 星盘 · AI 解盘 · 叙事化配音",
      },
      {
        label: "灵签",
        href: "/qian",
        desc: "摇签 · 观音灵签 · AI 解签",
      },
    ],
  },
];

// ---------------------------------------------------------------------------
// Gold hairline divider between panels
// ---------------------------------------------------------------------------
function PanelDivider({ narrow }: { narrow: boolean }) {
  return (
    <div
      style={{
        width: narrow ? 8 : 22,
        flexShrink: 0,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        transition: "width 0.4s ease",
      }}
      aria-hidden="true"
    >
      <div
        style={{
          width: 1,
          height: "78%",
          background:
            "linear-gradient(transparent,rgba(214,168,74,.5),transparent)",
        }}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sliver panel (collapsed to 66px when another is expanded)
// ---------------------------------------------------------------------------
function SliverPanel({
  domain,
  onClick,
}: {
  domain: Domain;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      aria-expanded={false}
      aria-label={domain.titleCn}
      onClick={onClick}
      className="screen-panel-sliver"
      style={{
        width: 66,
        height: 392,
        position: "relative",
        borderRadius: 8,
        overflow: "hidden",
        border: "1px solid #2c2417",
        background: domain.bgCollapsed,
        cursor: "pointer",
        flexShrink: 0,
        transition: "flex 0.4s ease, width 0.4s ease",
        // reset button styles
        padding: 0,
        outline: "none",
        appearance: "none",
      }}
    >
      {/* accent dot */}
      <span
        style={{
          position: "absolute",
          top: 10,
          left: "50%",
          transform: "translateX(-50%)",
          width: 6,
          height: 6,
          borderRadius: "50%",
          background: domain.accent,
          display: "block",
        }}
      />
      {/* vertical name */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          writingMode: "vertical-rl",
          fontSize: 18,
          letterSpacing: 6,
          color: "#7e948c",
          fontFamily: SERIF,
        }}
      >
        {domain.nameCnVertical.split(" · ")[0]} · {domain.enLabel}
      </div>
    </button>
  );
}

// ---------------------------------------------------------------------------
// Equal panel (all three at flex:1 when nothing expanded)
// ---------------------------------------------------------------------------
function EqualPanel({
  domain,
  onClick,
}: {
  domain: Domain;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      aria-expanded={false}
      aria-label={domain.titleCn}
      onClick={onClick}
      className="screen-panel-equal"
      style={{
        position: "relative",
        flex: 1,
        height: 392,
        borderRadius: 10,
        overflow: "hidden",
        border: "1px solid #2c2417",
        background: domain.bgCollapsed,
        cursor: "pointer",
        transition: "flex 0.4s ease",
        // reset button styles
        padding: 0,
        outline: "none",
        appearance: "none",
        textAlign: "left",
      }}
    >
      {/* top-left motif */}
      <div
        style={{ position: "absolute", top: 14, left: 16 }}
        aria-hidden="true"
      >
        {domain.key === "xue" ? CloudMotif : domain.motif}
      </div>

      {/* giant watermark char */}
      <div
        style={{
          position: "absolute",
          left: "50%",
          bottom: 46,
          transform: "translateX(-50%)",
          fontSize: 206,
          lineHeight: 0.78,
          fontWeight: 500,
          opacity: 0.19,
          color: domain.accent,
          fontFamily: SERIF,
          pointerEvents: "none",
          userSelect: "none",
          whiteSpace: "nowrap",
        }}
        aria-hidden="true"
      >
        {domain.char}
      </div>

      {/* base mist */}
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          bottom: 0,
          height: 120,
          background: `linear-gradient(transparent,rgba(${hexToRgb(domain.accent)},.10),rgba(10,17,15,.6))`,
        }}
        aria-hidden="true"
      />

      {/* vertical realm name */}
      <div
        style={{
          position: "absolute",
          top: 40,
          left: 16,
          writingMode: "vertical-rl",
          fontSize: 19,
          letterSpacing: 6,
          color: domain.nameColor,
          fontFamily: SERIF,
        }}
      >
        {domain.nameCnVertical}
      </div>

      {/* index bottom */}
      <div
        style={{
          position: "absolute",
          left: 16,
          right: 12,
          bottom: 14,
        }}
      >
        <div
          style={{
            fontSize: 12,
            color: "#9fb5ad",
            fontFamily: "system-ui",
          }}
        >
          {domain.indexLabel}
        </div>
        <div
          style={{
            fontSize: 11,
            color: "#7e948c",
            fontFamily: "system-ui",
            marginTop: 3,
          }}
        >
          {domain.indexLine}
        </div>
      </div>
    </button>
  );
}

// ---------------------------------------------------------------------------
// Expanded panel
// ---------------------------------------------------------------------------
function ExpandedPanel({
  domain,
  onCollapse,
}: {
  domain: Domain;
  onCollapse: () => void;
}) {
  return (
    <div
      style={{
        flex: 1,
        height: 392,
        position: "relative",
        borderRadius: 10,
        overflow: "hidden",
        border: `1px solid ${domain.borderExpanded}`,
        background: domain.bgExpanded,
        transition: "flex 0.4s ease",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* giant watermark char (right / bottom) */}
      <div
        style={{
          position: "absolute",
          right: -30,
          bottom: -40,
          fontSize: 300,
          lineHeight: 0.7,
          color: domain.accent,
          opacity: 0.12,
          fontWeight: 500,
          fontFamily: SERIF,
          pointerEvents: "none",
          userSelect: "none",
        }}
        aria-hidden="true"
      >
        {domain.char}
      </div>

      {/* header — clickable to collapse */}
      <button
        type="button"
        aria-expanded={true}
        aria-label={`${domain.titleCn} — 收起`}
        onClick={onCollapse}
        style={{
          display: "block",
          width: "100%",
          textAlign: "left",
          background: "none",
          border: "none",
          cursor: "pointer",
          padding: "22px 22px 0",
          flexShrink: 0,
          outline: "none",
        }}
      >
        <div
          style={{
            fontSize: 12,
            letterSpacing: 4,
            color: domain.accentLight,
            fontFamily: "system-ui",
          }}
        >
          {domain.numeral} · {domain.enLabel.toUpperCase()}
        </div>
        <div
          style={{
            fontSize: 30,
            color: "#efe7ff",
            marginTop: 4,
            fontFamily: SERIF,
          }}
        >
          {domain.titleCn}
        </div>
        <div
          style={{
            fontSize: 12.5,
            color: "#9486c4",
            fontFamily: "system-ui",
            marginTop: 4,
          }}
        >
          {domain.tagline}
        </div>
      </button>

      {/* sub-entries scrollable */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 10,
          padding: "16px 22px 14px",
          overflowY: "auto",
          flex: 1,
        }}
      >
        {domain.subs.map((sub) => (
          <Link
            key={sub.href}
            href={sub.href}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 14,
              padding: "12px 14px",
              border: "1px solid rgba(214,168,74,.22)",
              borderRadius: 12,
              background: "rgba(28,20,44,.5)",
              cursor: "pointer",
              textDecoration: "none",
              transition: "background 0.2s ease",
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLAnchorElement).style.background =
                "rgba(40,28,60,.7)";
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLAnchorElement).style.background =
                "rgba(28,20,44,.5)";
            }}
          >
            {/* motif icon */}
            <div style={{ flexShrink: 0, opacity: 0.8 }}>{domain.motif}</div>

            {/* label + desc */}
            <div style={{ flex: 1, minWidth: 0 }}>
              <div
                style={{
                  fontSize: 15,
                  fontWeight: 300,
                  color: "#e8e0f0",
                  fontFamily: SERIF,
                  lineHeight: 1.3,
                }}
              >
                {sub.label}
              </div>
              <div
                style={{
                  fontSize: 11.5,
                  color: "#7e6f9c",
                  fontFamily: "system-ui",
                  marginTop: 2,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {sub.desc}
              </div>
            </div>

            {/* enter arrow */}
            <span
              style={{
                fontSize: 18,
                color: domain.accentLight,
                flexShrink: 0,
              }}
              aria-hidden="true"
            >
              入 →
            </span>
          </Link>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Helper: hex → "r,g,b" for rgba()
// ---------------------------------------------------------------------------
function hexToRgb(hex: string): string {
  const clean = hex.replace("#", "");
  const r = parseInt(clean.substring(0, 2), 16);
  const g = parseInt(clean.substring(2, 4), 16);
  const b = parseInt(clean.substring(4, 6), 16);
  return `${r},${g},${b}`;
}

// ---------------------------------------------------------------------------
// Mobile accordion panel
// ---------------------------------------------------------------------------
function MobileBand({
  domain,
  isExpanded,
  onToggle,
}: {
  domain: Domain;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  return (
    <div
      style={{
        borderRadius: 10,
        overflow: "hidden",
        border: isExpanded
          ? `1px solid ${domain.borderExpanded}`
          : "1px solid #2c2417",
        background: isExpanded ? domain.bgExpanded : domain.bgCollapsed,
        transition: "background 0.3s ease",
      }}
    >
      {/* header band */}
      <button
        type="button"
        aria-expanded={isExpanded}
        aria-label={domain.titleCn}
        onClick={onToggle}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 14,
          width: "100%",
          padding: "16px 18px",
          background: "none",
          border: "none",
          cursor: "pointer",
          textAlign: "left",
          outline: "none",
        }}
      >
        {/* accent dot */}
        <span
          style={{
            width: 8,
            height: 8,
            borderRadius: "50%",
            background: domain.accent,
            flexShrink: 0,
            display: "block",
          }}
        />

        {/* name */}
        <div
          style={{
            fontSize: 17,
            letterSpacing: 4,
            color: isExpanded ? domain.nameColor : "#9fb5ad",
            fontFamily: SERIF,
            flex: 1,
          }}
        >
          {domain.nameCnVertical}
        </div>

        {/* label */}
        <div
          style={{
            fontSize: 11,
            color: "#7e948c",
            fontFamily: "system-ui",
            letterSpacing: 1,
          }}
        >
          {domain.numeral} · {domain.enLabel}
        </div>

        {/* chevron */}
        <span
          style={{
            fontSize: 14,
            color: domain.accent,
            transform: isExpanded ? "rotate(180deg)" : "rotate(0deg)",
            transition: "transform 0.3s ease",
            display: "inline-block",
          }}
          aria-hidden="true"
        >
          ▾
        </span>
      </button>

      {/* expanded content */}
      {isExpanded && (
        <div
          style={{
            padding: "0 18px 16px",
            display: "flex",
            flexDirection: "column",
            gap: 8,
          }}
        >
          <div
            style={{
              fontSize: 11.5,
              color: "#9486c4",
              fontFamily: "system-ui",
              paddingBottom: 10,
            }}
          >
            {domain.tagline}
          </div>
          {domain.subs.map((sub) => (
            <Link
              key={sub.href}
              href={sub.href}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 12,
                padding: "11px 14px",
                border: "1px solid rgba(214,168,74,.22)",
                borderRadius: 10,
                background: "rgba(28,20,44,.5)",
                textDecoration: "none",
              }}
            >
              <div style={{ flex: 1, minWidth: 0 }}>
                <div
                  style={{
                    fontSize: 14,
                    fontWeight: 300,
                    color: "#e8e0f0",
                    fontFamily: SERIF,
                  }}
                >
                  {sub.label}
                </div>
                <div
                  style={{
                    fontSize: 11,
                    color: "#7e6f9c",
                    fontFamily: "system-ui",
                    marginTop: 2,
                  }}
                >
                  {sub.desc}
                </div>
              </div>
              <span
                style={{ fontSize: 16, color: domain.accentLight }}
                aria-hidden="true"
              >
                入 →
              </span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------
export default function FoldingScreenHub() {
  const [expanded, setExpanded] = useState<string | null>(null);

  function handlePanelClick(key: string) {
    setExpanded((prev) => (prev === key ? null : key));
  }

  function handleCollapse() {
    setExpanded(null);
  }

  const hasExpanded = expanded !== null;

  return (
    <>
      {/* Reduced-motion + panel transition styles */}
      <style>{`
        .screen-panel-equal,
        .screen-panel-sliver {
          transition: flex 0.4s ease, width 0.4s ease;
        }
        @media (prefers-reduced-motion: reduce) {
          .screen-panel-equal,
          .screen-panel-sliver {
            transition: none !important;
          }
        }
      `}</style>

      {/* Outer lacquer frame */}
      <div
        style={{
          padding: 13,
          borderRadius: 18,
          background: "linear-gradient(135deg,#3a1a0c,#1c0d06)",
          boxShadow:
            "inset 0 0 0 2px rgba(202,164,74,.55),inset 0 0 0 11px #190b05,inset 0 0 0 12px rgba(202,164,74,.35)",
          fontFamily: SERIF,
        }}
      >
        {/* Masthead */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 11,
            padding: "2px 6px 12px",
          }}
        >
          {/* Avatar seal */}
          <div
            style={{
              width: 28,
              height: 28,
              borderRadius: 5,
              background: "#b9472f",
              color: "#f3e6cf",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 17,
              fontFamily: SERIF,
              flexShrink: 0,
            }}
            aria-hidden="true"
          >
            磊
          </div>

          {/* Portal name */}
          <div
            style={{
              fontSize: 18,
              color: "#ecdfc6",
              letterSpacing: 3,
              fontFamily: SERIF,
            }}
          >
            方寸
          </div>

          {/* Domain legend */}
          <div
            style={{
              marginLeft: "auto",
              fontSize: 10.5,
              color: "#9c8456",
              letterSpacing: 1,
              fontFamily: "system-ui",
            }}
            aria-hidden="true"
          >
            学 · 造 · 玄
          </div>
        </div>

        {/* ----------------------------------------------------------------
            DESKTOP layout (lg+): horizontal panels row
            MOBILE: hidden here, shown via the mobile accordion below
        ---------------------------------------------------------------- */}
        <div className="hidden lg:flex" style={{ gap: 0 }}>
          {DOMAINS.map((domain, idx) => {
            const isExp = expanded === domain.key;
            const isSliver = hasExpanded && !isExp;

            return (
              <React.Fragment key={domain.key}>
                {idx > 0 && <PanelDivider narrow={hasExpanded} />}

                {isSliver ? (
                  <SliverPanel
                    domain={domain}
                    onClick={() => handlePanelClick(domain.key)}
                  />
                ) : isExp ? (
                  <ExpandedPanel
                    domain={domain}
                    onCollapse={handleCollapse}
                  />
                ) : (
                  <EqualPanel
                    domain={domain}
                    onClick={() => handlePanelClick(domain.key)}
                  />
                )}
              </React.Fragment>
            );
          })}
        </div>

        {/* ----------------------------------------------------------------
            MOBILE layout (< lg): vertical accordion
        ---------------------------------------------------------------- */}
        <div
          className="flex lg:hidden"
          style={{ flexDirection: "column", gap: 8 }}
        >
          {DOMAINS.map((domain) => (
            <MobileBand
              key={domain.key}
              domain={domain}
              isExpanded={expanded === domain.key}
              onToggle={() => handlePanelClick(domain.key)}
            />
          ))}
        </div>
      </div>
    </>
  );
}
