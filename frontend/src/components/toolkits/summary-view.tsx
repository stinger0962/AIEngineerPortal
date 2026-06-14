"use client";

export interface Section {
  heading: string;
  points: string[];
}

export interface Summary {
  id: number;
  source_type: string;
  source_url: string | null;
  title: string;
  tldr: string;
  sections: Section[];
  output_type: "summary" | "mindmap";
  mindmap_md: string | null;
  char_count: number;
  created_at: string;
}

export function SummaryView({ summary }: { summary: Summary }) {
  return (
    <div className="space-y-4">
      {/* TL;DR — most prominent */}
      <div className="rounded-2xl border border-[#c0892e]/20 bg-[#c0892e]/5 p-4">
        <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#c0892e]/70 mb-1">
          TL;DR
        </p>
        <p className="text-base font-medium text-ink leading-relaxed">{summary.tldr}</p>
      </div>

      {/* Adaptive sections — headings chosen by the model per content type */}
      {summary.sections.map((sec, i) => (
        <div key={i}>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-ink/40 mb-2">
            {sec.heading}
          </p>
          <ul className="space-y-1.5">
            {sec.points.map((p, j) => (
              <li key={j} className="flex gap-2 text-sm text-ink/80 leading-relaxed">
                <span className="text-[#c0892e] flex-shrink-0">•</span>
                <span>{p}</span>
              </li>
            ))}
          </ul>
        </div>
      ))}

      {/* Source link */}
      {summary.source_url && (
        <a
          href={summary.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-block text-[11px] text-ink/40 hover:text-[#c0892e] transition-colors break-all"
        >
          🔗 {summary.source_url}
        </a>
      )}
    </div>
  );
}
