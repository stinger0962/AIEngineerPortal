import type { Metadata } from "next";

const title = "蒸馏所 · 配 Dub";
const description = "把外语 YouTube 视频配成中文旁白视频 —— 原声压低做背景，配音对齐时间轴。";

export const metadata: Metadata = {
  title,
  description,
  openGraph: { title, description, type: "website", siteName: "AI Engineer Portal", locale: "zh_CN" },
  twitter: { card: "summary_large_image", title, description },
};

export default function DubLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
