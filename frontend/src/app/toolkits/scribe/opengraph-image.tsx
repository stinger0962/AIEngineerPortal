import { renderOgCard, OG_SIZE, OG_CONTENT_TYPE } from "../../_og/card";

export const runtime = "nodejs";
export const size = OG_SIZE;
export const contentType = OG_CONTENT_TYPE;
export const alt = "蒸馏所 · 录 Scribe";

export default function Image() {
  return renderOgCard({
    char: "录",
    title: "蒸馏所 · 录 Scribe",
    category: "视频 → 文字稿",
    accent: "#4f46e5",
  });
}
