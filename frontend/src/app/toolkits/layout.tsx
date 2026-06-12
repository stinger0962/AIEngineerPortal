import type { Metadata } from "next";

const title = "蒸馏所 · Distill";
const description = "万物皆可蒸馏。一组把视频、网页、文章提炼成你真正用得上形式的小工具。";

export const metadata: Metadata = {
  title,
  description,
  openGraph: { title, description, type: "website", siteName: "AI Engineer Portal", locale: "zh_CN" },
  twitter: { card: "summary_large_image", title, description },
};

export default function ToolkitsLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
