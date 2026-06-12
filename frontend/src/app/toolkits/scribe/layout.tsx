import type { Metadata } from "next";

const title = "蒸馏所 · 录 Scribe";
const description = "把无字幕的 YouTube 视频用 Whisper 录成文字稿 —— 原语言逐字转写，可复制下载。";

export const metadata: Metadata = {
  title,
  description,
  openGraph: { title, description, type: "website", siteName: "AI Engineer Portal", locale: "zh_CN" },
  twitter: { card: "summary_large_image", title, description },
};

export default function ScribeLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
