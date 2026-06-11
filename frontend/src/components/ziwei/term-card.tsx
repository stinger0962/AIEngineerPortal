"use client";

export type TermInfo = { term: string; explanation: string };

export function TermCard({ info, onClose }: { info: TermInfo; onClose: () => void }) {
  return (
    <div className="absolute bottom-4 left-4 z-20 max-w-xs rounded-2xl border border-violet-400/40 bg-[#160b38]/95 p-4 shadow-[0_8px_30px_rgba(91,33,182,0.45)] backdrop-blur">
      <div className="mb-1 flex items-start justify-between gap-3">
        <span className="text-sm font-semibold tracking-wide text-amber-200">{info.term}</span>
        <button type="button" onClick={onClose} aria-label="关闭释义" className="text-violet-300/60 hover:text-violet-100">
          ✕
        </button>
      </div>
      <p className="text-xs leading-relaxed text-violet-200/85">{info.explanation}</p>
    </div>
  );
}
