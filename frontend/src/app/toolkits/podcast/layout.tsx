import type { Metadata } from "next";

const title = "蒸馏所 · 炼 Forge";
const description = "把一条 YouTube 视频炼成一期中文播客 —— 单人讲述或双人对话，原生普通话配音。";

export const metadata: Metadata = {
  title,
  description,
  openGraph: { title, description, type: "website", siteName: "AI Engineer Portal", locale: "zh_CN" },
  twitter: { card: "summary", title, description },
};

export default function ForgeLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
