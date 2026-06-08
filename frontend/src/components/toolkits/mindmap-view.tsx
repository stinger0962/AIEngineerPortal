"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Transformer } from "markmap-lib";
import { Markmap } from "markmap-view";
import { Maximize2, X } from "lucide-react";

const transformer = new Transformer();

/**
 * Owns a single markmap instance bound to its own <svg>. Creating one per mount
 * (inline vs fullscreen) keeps the two views independent and correctly sized to
 * their container. markmap only touches the DOM inside the effect, so SSR-safe.
 */
function MarkmapCanvas({ markdown }: { markdown: string }) {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const mmRef = useRef<Markmap | null>(null);

  useEffect(() => {
    if (!svgRef.current) return;
    try {
      const { root } = transformer.transform(markdown || "# ");
      mmRef.current = Markmap.create(svgRef.current, { duration: 300, paddingX: 16 }, root);
      // Fit after a tick so the container has its final size (esp. in the overlay).
      const t = setTimeout(() => mmRef.current?.fit(), 60);
      return () => {
        clearTimeout(t);
        mmRef.current?.destroy();
        mmRef.current = null;
      };
    } catch {
      // swallow render errors; parent shows a fallback when markdown is empty
    }
  }, [markdown]);

  return <svg ref={svgRef} className="w-full h-full" />;
}

export function MindMapView({ markdown }: { markdown: string }) {
  const [isFull, setIsFull] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  // While fullscreen: lock body scroll and close on Escape.
  useEffect(() => {
    if (!isFull) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setIsFull(false);
    };
    window.addEventListener("keydown", onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [isFull]);

  if (!markdown) {
    return (
      <div className="rounded-xl border border-ink/10 bg-white p-4 text-sm text-ink/40">
        无法渲染思维导图
      </div>
    );
  }

  const overlay = (
    <div className="fixed inset-0 z-[100] bg-white flex flex-col">
      <div className="flex items-center justify-between px-4 py-3 border-b border-ink/10">
        <span className="flex items-center gap-2 text-sm font-semibold text-ink">
          <span className="text-teal" aria-hidden="true">🧠</span> 思维导图
        </span>
        <button
          onClick={() => setIsFull(false)}
          aria-label="关闭全屏"
          className="flex items-center justify-center w-10 h-10 rounded-lg text-ink/50 hover:text-ink hover:bg-ink/5 transition-colors"
        >
          <X className="w-5 h-5" strokeWidth={2} />
        </button>
      </div>
      <div className="flex-1 overflow-hidden">
        {/* Fresh instance keyed so it rebuilds and fits the full viewport */}
        <MarkmapCanvas key="full" markdown={markdown} />
      </div>
    </div>
  );

  return (
    <>
      <div className="relative w-full h-[360px] lg:h-[460px] rounded-xl border border-ink/10 bg-white overflow-hidden">
        <MarkmapCanvas key="inline" markdown={markdown} />
        <button
          onClick={() => setIsFull(true)}
          aria-label="全屏查看思维导图"
          title="全屏"
          className="absolute top-2 right-2 z-10 flex items-center justify-center w-9 h-9 rounded-lg bg-white/90 border border-ink/10 text-ink/50 hover:text-teal hover:border-teal/40 shadow-sm transition-colors"
        >
          <Maximize2 className="w-4 h-4" strokeWidth={2} />
        </button>
      </div>

      {isFull && mounted && createPortal(overlay, document.body)}
    </>
  );
}
