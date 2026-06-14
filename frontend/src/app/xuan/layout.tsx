import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "命理 · 玄",
  description: "紫微斗数与灵签 —— 问一事，观天机。",
  openGraph: {
    title: "命理 · 玄",
    description: "紫微斗数与灵签 —— 问一事，观天机。",
    type: "website",
    siteName: "AI Engineer Portal",
    locale: "zh_CN",
  },
  twitter: {
    card: "summary_large_image",
    title: "命理 · 玄",
    description: "紫微斗数与灵签 —— 问一事，观天机。",
  },
};

export default function XuanLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
