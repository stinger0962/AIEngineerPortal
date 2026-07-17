import { renderOgCard, OG_SIZE, OG_CONTENT_TYPE } from "../../_og/card";

// og-layout: centered v2 — bump content so Next mints a fresh ?hash (busts stale crop).
export const runtime = "nodejs";
export const size = OG_SIZE;
export const contentType = OG_CONTENT_TYPE;
export const alt = "蒸馏所 · 炼 Forge";

export default function Image() {
  return renderOgCard({
    char: "炼",
    title: "蒸馏所 · 炼 Forge",
    category: "视频 → 播客",
    accent: "#f77f00",
  });
}
