"use client";

import { useEffect, useRef } from "react";
import { Transformer } from "markmap-lib";
import { Markmap } from "markmap-view";

const transformer = new Transformer();

export function MindMapView({ markdown }: { markdown: string }) {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const mmRef = useRef<Markmap | null>(null);

  useEffect(() => {
    if (!svgRef.current) return;
    try {
      const { root } = transformer.transform(markdown || "# ");
      if (!mmRef.current) {
        mmRef.current = Markmap.create(svgRef.current, { duration: 300, paddingX: 16 }, root);
      } else {
        mmRef.current.setData(root);
      }
      mmRef.current.fit();
    } catch {
      // swallow render errors; the empty-markdown fallback below covers the no-data case
    }
    return () => {
      mmRef.current?.destroy();
      mmRef.current = null;
    };
  }, [markdown]);

  if (!markdown) {
    return (
      <div className="rounded-xl border border-ink/10 bg-white p-4 text-sm text-ink/40">
        无法渲染思维导图
      </div>
    );
  }

  return (
    <div className="w-full h-[360px] lg:h-[460px] rounded-xl border border-ink/10 bg-white overflow-hidden">
      <svg ref={svgRef} className="w-full h-full" />
    </div>
  );
}
