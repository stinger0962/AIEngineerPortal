import { renderOgCard, OG_SIZE, OG_CONTENT_TYPE } from "../../_og/card";

export const runtime = "nodejs";
export const size = OG_SIZE;
export const contentType = OG_CONTENT_TYPE;
export const alt = "蒸馏所 · 配 Dub";

export default function Image() {
  return renderOgCard({
    char: "配",
    title: "蒸馏所 · 配 Dub",
    category: "外语视频 → 中文配音",
    accent: "#e11d48",
  });
}
