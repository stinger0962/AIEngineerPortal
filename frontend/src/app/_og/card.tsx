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
  // 居中构图：聊天软件（微信等）会把 1200×630 裁成中心正方形缩略图，
  // 内容必须落在中央安全区，否则边缘被切（旧版把书法字放最左 → 缩略图只剩右半）。
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: bg,
          backgroundImage: `radial-gradient(760px 620px at 50% 40%, ${accent}30 0%, ${accent}00 62%)`,
          fontFamily: "NotoSC",
          color: "#f6f6fb",
          position: "relative",
          textAlign: "center",
        }}
      >
        {/* 顶部小标 */}
        <div style={{ display: "flex", fontSize: 28, letterSpacing: 8, color: accent, marginBottom: 30 }}>
          {eyebrow}
        </div>

        {/* 书法字圆章（居中焦点，正方形裁切也完整） */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: 232,
            height: 232,
            borderRadius: 116,
            border: `4px solid ${accent}`,
            backgroundColor: `${accent}18`,
            color: accent,
            fontSize: 148,
            lineHeight: 1,
            marginBottom: 34,
          }}
        >
          {char}
        </div>

        {/* 标题 */}
        <div style={{ display: "flex", fontSize: 74, fontWeight: 700, marginBottom: 18 }}>{title}</div>

        {/* 副标 */}
        <div style={{ display: "flex", fontSize: 34, color: "#b9b9c8" }}>{category}</div>

        {/* 站点（底部，非安全区无妨） */}
        <div style={{ display: "flex", position: "absolute", bottom: 42, fontSize: 24, color: "#6f6f80" }}>
          portal.leipan.cc
        </div>
      </div>
    ),
    {
      ...OG_SIZE,
      fonts: [{ name: "NotoSC", data: font(), style: "normal", weight: 400 }],
    },
  );
}
