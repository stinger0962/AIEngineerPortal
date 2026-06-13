"use client";
import { Scroll } from "lucide-react";
import { QianWorkspace } from "@/components/qian/qian-workspace";

export default function QianPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-[14px] bg-gradient-to-br from-[#d6a84a] to-[#b9472f] text-[#140e08] shadow-[0_6px_16px_-6px_rgba(214,168,74,0.6)]">
          <Scroll className="h-6 w-6" strokeWidth={2} />
        </div>
        <div>
          <span className="text-xs font-semibold uppercase tracking-[0.28em] text-[#b9472f]">观音灵签 · Oracle</span>
          <h1 className="font-display text-2xl leading-tight text-ink">灵签</h1>
        </div>
      </div>
      <p className="text-sm text-ink/55">静心默想所问之事，再摇签。签为公版古诗，解签仅供参考、博君一宽。</p>
      <QianWorkspace />
    </div>
  );
}
