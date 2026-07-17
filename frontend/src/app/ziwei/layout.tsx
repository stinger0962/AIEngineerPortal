import type { Metadata } from "next";

const title = "紫微斗数 · 星盘命理";
const description = "输入生辰起盘，3D 星盘徐徐飞入，AI 解盘师为你解读命宫格局与流年运势。";

export const metadata: Metadata = {
  title,
  description,
  openGraph: { title, description, type: "website", siteName: "AI Engineer Portal", locale: "zh_CN" },
  twitter: { card: "summary_large_image", title, description },
};

export default function ZiweiLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
