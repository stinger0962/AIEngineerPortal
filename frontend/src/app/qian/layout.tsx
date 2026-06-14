import type { Metadata } from "next";

const title = "灵签 · 观音灵签求签";
const description = "静心问一事，摇一支观音灵签，AI 解签人为你解读签诗。";

export const metadata: Metadata = {
  title,
  description,
  openGraph: { title, description, type: "website", siteName: "AI Engineer Portal", locale: "zh_CN" },
  twitter: { card: "summary_large_image", title, description },
};

export default function QianLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
