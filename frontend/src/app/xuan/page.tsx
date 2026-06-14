import Link from "next/link";

import { DoorLink } from "@/components/transitions/door-link";

const SERIF = "'Songti SC','Noto Serif CJK SC','STSong','SimSun',serif";

export default function XuanPage() {
  return (
    <>
      {/* Scoped hover styles — no external deps, no JS required */}
      <style>{`
        .xuan-door {
          transition: border-color .35s ease, box-shadow .35s ease, transform .35s ease;
        }
        .xuan-door:hover,
        .xuan-door:focus-visible {
          transform: translateY(-2px);
        }
        .xuan-door--ziwei:hover,
        .xuan-door--ziwei:focus-visible {
          border-color: rgba(154,123,240,.72) !important;
          box-shadow: 0 18px 50px -28px rgba(154,123,240,.7);
        }
        .xuan-door--qian:hover,
        .xuan-door--qian:focus-visible {
          border-color: rgba(214,168,74,.72) !important;
          box-shadow: 0 18px 50px -28px rgba(214,168,74,.6);
        }
        @media (prefers-reduced-motion: reduce) {
          .xuan-door { transition: none; }
        }
      `}</style>

      <div
        style={{
          minHeight: "100dvh",
          background: "radial-gradient(130% 95% at 50% -6%, #1a1330, #0c0a18 55%)",
          display: "flex",
          flexDirection: "column",
          fontFamily: SERIF,
        }}
      >
        {/* ── Top strip ── */}
        <header
          style={{
            padding: "clamp(16px,3vh,26px) clamp(20px,4vw,46px)",
            display: "flex",
            alignItems: "center",
            gap: 12,
            flexShrink: 0,
          }}
        >
          {/* Back to homepage */}
          <Link
            href="/"
            style={{
              color: "#9486c4",
              fontSize: 12.5,
              fontFamily: "system-ui,sans-serif",
              textDecoration: "none",
              transition: "color .2s",
            }}
            onMouseEnter={undefined}
            className="xuan-back-link"
          >
            ← 方寸 · 首页
          </Link>

          {/* 磊 seal */}
          <div
            style={{
              width: 22,
              height: 22,
              borderRadius: 4,
              background: "#b9472f",
              color: "#f3e6cf",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 13,
              flexShrink: 0,
              fontFamily: SERIF,
            }}
            aria-hidden="true"
          >
            磊
          </div>

          {/* Wordmark */}
          <span
            style={{
              fontSize: 16,
              letterSpacing: 4,
              color: "#efe7ff",
              fontFamily: SERIF,
            }}
          >
            命理 · 玄
          </span>
        </header>

        {/* ── Body — two doors ── */}
        <main
          className="flex flex-col lg:flex-row"
          style={{
            flex: 1,
            gap: 16,
            padding: "0 clamp(14px,3vw,40px) clamp(20px,3vh,40px)",
            minHeight: 0,
          }}
        >
          {/* ── Door 1: 紫微斗数 ── */}
          <DoorLink
            href="/ziwei"
            theme={{ char: "紫", accent: "#9a7bf0", innerBg: "linear-gradient(#171036,#0e0a1f)" }}
            ariaLabel="紫微斗数 · 入口"
            className="xuan-door xuan-door--ziwei"
            style={{
              flex: 1,
              alignSelf: "stretch",
              minHeight: 0,
              position: "relative",
              overflow: "hidden",
              borderRadius: 12,
              border: "1px solid rgba(154,123,240,.34)",
              background:
                "radial-gradient(120% 80% at 75% 105%, rgba(154,123,240,.24), #0d0a1c 62%)",
              textDecoration: "none",
              cursor: "pointer",
              display: "block",
            }}
          >
            {/* 北斗 star motif — top left */}
            <svg
              width="48"
              height="44"
              viewBox="0 0 48 44"
              aria-hidden="true"
              style={{ position: "absolute", top: 26, left: 24 }}
            >
              <g fill="#c9b6ff">
                <circle cx="10" cy="12" r="1.7" />
                <circle cx="20" cy="8" r="1.7" />
                <circle cx="29" cy="14" r="1.7" />
                <circle cx="38" cy="10" r="1.7" />
                <circle cx="41" cy="20" r="1.7" />
                <circle cx="34" cy="27" r="1.7" />
                <circle cx="25" cy="26" r="1.7" />
              </g>
              <path
                d="M10 12l10-4 9 6 9-4 3 10-7 7-9-1z"
                fill="none"
                stroke="#9a7bf0"
                strokeWidth="1"
                opacity=".6"
              />
            </svg>

            {/* Giant watermark char */}
            <span
              aria-hidden="true"
              style={{
                position: "absolute",
                right: -16,
                bottom: -30,
                fontSize: "min(34vh, 300px)",
                lineHeight: 0.7,
                color: "#9a7bf0",
                opacity: 0.16,
                pointerEvents: "none",
                fontFamily: SERIF,
                userSelect: "none",
              }}
            >
              紫
            </span>

            {/* Vertical name */}
            <span
              aria-hidden="true"
              style={{
                position: "absolute",
                top: 90,
                left: 26,
                writingMode: "vertical-rl",
                fontSize: "clamp(20px,2.4vh,26px)",
                letterSpacing: 6,
                color: "#cdbfff",
                fontFamily: SERIF,
              }}
            >
              紫微斗数
            </span>

            {/* Numeral + EN — top right */}
            <div
              style={{
                position: "absolute",
                top: 26,
                right: 24,
                textAlign: "right",
                display: "flex",
                flexDirection: "column",
                gap: 2,
              }}
            >
              <span style={{ fontFamily: SERIF, fontSize: 17, color: "#cdbfff" }}>壹</span>
              <span
                style={{
                  fontFamily: "system-ui,sans-serif",
                  fontSize: 10.5,
                  letterSpacing: 3,
                  color: "#9a7bf0",
                  opacity: 0.85,
                }}
              >
                ZIWEI
              </span>
            </div>

            {/* Bottom row */}
            <div
              style={{
                position: "absolute",
                left: 24,
                right: 22,
                bottom: 22,
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-end",
              }}
            >
              <span
                style={{
                  fontSize: 11.5,
                  color: "rgba(255,255,255,.45)",
                  fontFamily: "system-ui,sans-serif",
                }}
              >
                3D 星盘 · AI 解盘 · 叙事配音
              </span>
              <span style={{ fontSize: 15, letterSpacing: 2, color: "#bcaaf0", fontFamily: SERIF }}>
                入口 →
              </span>
            </div>

            {/* Base mist overlay */}
            <div
              aria-hidden="true"
              style={{
                position: "absolute",
                bottom: 0,
                left: 0,
                right: 0,
                height: "34%",
                background: "linear-gradient(transparent, rgba(0,0,0,.45))",
                pointerEvents: "none",
              }}
            />
          </DoorLink>

          {/* ── Door 2: 灵签 ── */}
          <DoorLink
            href="/qian"
            theme={{ char: "灵", accent: "#d6a84a", innerBg: "linear-gradient(#1c1408,#120c05)" }}
            ariaLabel="灵签求签 · 入口"
            className="xuan-door xuan-door--qian"
            style={{
              flex: 1,
              alignSelf: "stretch",
              minHeight: 0,
              position: "relative",
              overflow: "hidden",
              borderRadius: 12,
              border: "1px solid rgba(214,168,74,.42)",
              background:
                "radial-gradient(120% 80% at 75% 105%, rgba(214,168,74,.20), #120c05 62%)",
              textDecoration: "none",
              cursor: "pointer",
              display: "block",
            }}
          >
            {/* Scroll motif — top left */}
            <svg
              width="34"
              height="40"
              viewBox="0 0 34 40"
              aria-hidden="true"
              style={{ position: "absolute", top: 26, left: 24 }}
            >
              <path
                d="M8 6h18M9 6v26c0 2 2 3 4 2l4-2 4 2c2 1 4 0 4-2V6M17 8v26"
                fill="none"
                stroke="#e7c372"
                strokeWidth="1.2"
                strokeLinecap="round"
              />
            </svg>

            {/* Giant watermark char */}
            <span
              aria-hidden="true"
              style={{
                position: "absolute",
                right: -16,
                bottom: -30,
                fontSize: "min(34vh, 300px)",
                lineHeight: 0.7,
                color: "#d6a84a",
                opacity: 0.16,
                pointerEvents: "none",
                fontFamily: SERIF,
                userSelect: "none",
              }}
            >
              灵
            </span>

            {/* Vertical name */}
            <span
              aria-hidden="true"
              style={{
                position: "absolute",
                top: 90,
                left: 26,
                writingMode: "vertical-rl",
                fontSize: "clamp(20px,2.4vh,26px)",
                letterSpacing: 6,
                color: "#e7c372",
                fontFamily: SERIF,
              }}
            >
              灵签求签
            </span>

            {/* Numeral + EN — top right */}
            <div
              style={{
                position: "absolute",
                top: 26,
                right: 24,
                textAlign: "right",
                display: "flex",
                flexDirection: "column",
                gap: 2,
              }}
            >
              <span style={{ fontFamily: SERIF, fontSize: 17, color: "#e7c372" }}>贰</span>
              <span
                style={{
                  fontFamily: "system-ui,sans-serif",
                  fontSize: 10.5,
                  letterSpacing: 3,
                  color: "#d6a84a",
                  opacity: 0.85,
                }}
              >
                QIAN
              </span>
            </div>

            {/* Bottom row */}
            <div
              style={{
                position: "absolute",
                left: 24,
                right: 22,
                bottom: 22,
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-end",
              }}
            >
              <span
                style={{
                  fontSize: 11.5,
                  color: "rgba(255,255,255,.45)",
                  fontFamily: "system-ui,sans-serif",
                }}
              >
                摇签 · 观音灵签 · AI 解签
              </span>
              <span style={{ fontSize: 15, letterSpacing: 2, color: "#f0c082", fontFamily: SERIF }}>
                入口 →
              </span>
            </div>

            {/* Base mist overlay */}
            <div
              aria-hidden="true"
              style={{
                position: "absolute",
                bottom: 0,
                left: 0,
                right: 0,
                height: "34%",
                background: "linear-gradient(transparent, rgba(0,0,0,.45))",
                pointerEvents: "none",
              }}
            />
          </DoorLink>
        </main>
      </div>

      {/* Back-link hover style (CSS-only, no JS) */}
      <style>{`
        .xuan-back-link:hover { color: #cdbfff !important; }
      `}</style>
    </>
  );
}
