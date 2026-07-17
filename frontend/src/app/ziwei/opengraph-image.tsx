import { renderOgCard, OG_SIZE, OG_CONTENT_TYPE } from "../_og/card";

export const runtime = "nodejs";
export const size = OG_SIZE;
export const contentType = OG_CONTENT_TYPE;
export const alt = "紫微斗数 · 星盘命理";

export default function Image() {
  return renderOgCard({
    char: "紫",
    title: "紫微斗数 · 星盘",
    category: "AI 解盘师为你解读命盘",
    accent: "#9a7bf0",
    eyebrow: "星垣 · Astrolabe",
    bg: "#0a0618",
  });
}
