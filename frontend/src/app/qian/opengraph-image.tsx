import { renderOgCard, OG_SIZE, OG_CONTENT_TYPE } from "../_og/card";

export const runtime = "nodejs";
export const size = OG_SIZE;
export const contentType = OG_CONTENT_TYPE;
export const alt = "灵签 · 观音灵签求签";

export default function Image() {
  return renderOgCard({
    char: "灵",
    title: "灵签 · 观音灵签",
    category: "摇一支签 · AI 为你解签",
    accent: "#d6a84a",
    eyebrow: "观音灵签 · Oracle",
    bg: "#140e08",
  });
}
