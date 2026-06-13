"use client";
import { QianWorkspace } from "@/components/qian/qian-workspace";

export default function QianPage() {
  return (
    <div className="space-y-6">
      {/* Temple wordmark header — sits on LIGHT portal background */}
      <div className="flex items-start gap-4">
        {/* Gold-bordered seal tile */}
        <div
          className="flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-[10px] border"
          style={{
            border: "1px solid #d6a84a",
            background: "linear-gradient(145deg,#fdf5e4,#f0ddb0)",
          }}
        >
          <span
            style={{
              fontFamily: "'STKaiti','KaiTi STD','KaiTi','楷体','Kaiti SC',serif",
              fontSize: "22px",
              color: "#e7c372",
              textShadow: "0 1px 3px rgba(130,70,10,.4)",
            }}
          >
            签
          </span>
        </div>
        <div className="flex flex-col gap-0.5">
          {/* Eyebrow */}
          <span
            className="text-[11px] font-semibold uppercase tracking-[0.22em]"
            style={{ color: "#9c6b1a" }}
          >
            Temple Oracle
          </span>
          {/* Wordmark */}
          <h1
            style={{
              fontFamily: "'STKaiti','KaiTi STD','KaiTi','楷体','Kaiti SC',serif",
              fontSize: "28px",
              letterSpacing: "2px",
              color: "#7a3b1d",
              lineHeight: 1.2,
            }}
          >
            观音灵签
          </h1>
        </div>
      </div>
      {/* Disclaimer */}
      <p className="text-sm" style={{ color: "#8a7350" }}>
        静心默想所问之事，再摇签。签为公版古诗，解签仅供参考、博君一宽。
      </p>
      <QianWorkspace />
    </div>
  );
}
