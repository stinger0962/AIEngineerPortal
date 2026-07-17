import { renderOgCard, OG_SIZE, OG_CONTENT_TYPE } from "../_og/card";

// og-layout: centered v2 — bump content so Next mints a fresh ?hash (busts stale crop).
export const runtime = "nodejs";
export const size = OG_SIZE;
export const contentType = OG_CONTENT_TYPE;
export const alt = "蒸馏所 · Distill";

export default function Image() {
  return renderOgCard({
    char: "蒸",
    title: "蒸馏所 · Distill",
    category: "万物皆可蒸馏 · Distill anything",
    accent: "#f77f00",
  });
}
