import { renderOgCard, OG_SIZE, OG_CONTENT_TYPE } from "../../_og/card";

export const runtime = "nodejs";
export const size = OG_SIZE;
export const contentType = OG_CONTENT_TYPE;
export const alt = "蒸馏所 · 织 Loom";

export default function Image() {
  return renderOgCard({
    char: "织",
    title: "蒸馏所 · 织 Loom",
    category: "内容 → 摘要",
    accent: "#1f6f6b",
  });
}
