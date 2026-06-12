import type { Metadata } from "next";

const title = "蒸馏所 · 织 Loom";
const description = "把文本、网页、YouTube 或微信文章织成结构化中文摘要 —— TL;DR、关键要点与核心收获。";

export const metadata: Metadata = {
  title,
  description,
  openGraph: { title, description, type: "website", siteName: "AI Engineer Portal", locale: "zh_CN" },
  twitter: { card: "summary", title, description },
};

export default function LoomLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
