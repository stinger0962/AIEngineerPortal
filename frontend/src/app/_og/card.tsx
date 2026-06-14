// 蒸馏所分享配图共享渲染器（next/og + 子集化中文字体）。
// 每个工具的 opengraph-image.tsx 调 renderOgCard 生成 1200×630 PNG。
import { ImageResponse } from "next/og";
import { readFileSync } from "node:fs";
import { join } from "node:path";

export const OG_SIZE = { width: 1200, height: 630 };
export const OG_CONTENT_TYPE = "image/png";

let _font: Buffer | null = null;
function font(): Buffer {
  // 字体随 public/ 一并拷进运行时镜像；进程 cwd 即应用根。懒加载 + 缓存。
  if (!_font) _font = readFileSync(join(process.cwd(), "public", "fonts", "og-font.ttf"));
  return _font;
}

type CardOpts = {
  char: string; // 蒸/炼/织/录/配/灵
  title: string; // 蒸馏所 · 配 Dub
  category: string; // 外语视频 → 中文配音
  accent: string; // hex 主色
  eyebrow?: string; // 顶部小标，默认蒸馏所；灵签等可覆盖
  bg?: string; // 底色，默认冷黑；庙宇等暖色可覆盖
};

export function renderOgCard({ char, title, category, accent, eyebrow = "蒸馏所 · Distill", bg = "#0b0b12" }: CardOpts) {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          backgroundColor: bg,
          backgroundImage: `radial-gradient(1100px 700px at 18% 28%, ${accent}38 0%, rgba(11,11,18,0) 60%)`,
          fontFamily: "NotoSC",
          color: "#f6f6fb",
          position: "relative",
        }}
      >
        {/* 左侧主色竖条 */}
        <div style={{ display: "flex", width: 14, height: "100%", backgroundColor: accent }} />

        {/* 巨大书法字 */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: 460,
            height: "100%",
            fontSize: 360,
            color: accent,
            lineHeight: 1,
          }}
        >
          {char}
        </div>

        {/* 右侧文案 */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            flex: 1,
            paddingRight: 84,
          }}
        >
          <div style={{ display: "flex", fontSize: 30, letterSpacing: 8, color: accent, marginBottom: 18 }}>
            {eyebrow}
          </div>
          <div style={{ display: "flex", fontSize: 84, fontWeight: 700, marginBottom: 22 }}>{title}</div>
          <div style={{ display: "flex", fontSize: 38, color: "#b9b9c8" }}>{category}</div>
          <div style={{ display: "flex", flex: 1 }} />
          <div style={{ display: "flex", fontSize: 26, color: "#6f6f80" }}>portal.leipan.cc</div>
        </div>
      </div>
    ),
    {
      ...OG_SIZE,
      fonts: [{ name: "NotoSC", data: font(), style: "normal", weight: 400 }],
    },
  );
}
