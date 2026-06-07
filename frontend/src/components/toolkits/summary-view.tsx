"use client";

export interface Summary {
  id: number;
  source_type: string;
  source_url: string | null;
  title: string;
  tldr: string;
  key_points: string[];
  takeaways: string[];
  char_count: number;
  created_at: string;
}

export function SummaryView({ summary }: { summary: Summary }) {
  return (
    <div className="space-y-4">
      <div className="rounded-2xl border border-teal/20 bg-teal/5 p-4">
        <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-teal/70 mb-1">
          TL;DR
        </p>
        <p className="text-base font-medium text-ink leading-relaxed">{summary.tldr}</p>
      </div>

      {summary.key_points.length > 0 && (
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-ink/40 mb-2">
            关键要点 Key Points
          </p>
          <ul className="space-y-1.5">
            {summary.key_points.map((p, i) => (
              <li key={i} className="flex gap-2 text-sm text-ink/80 leading-relaxed">
                <span className="text-teal flex-shrink-0">•</span>
                <span>{p}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {summary.takeaways.length > 0 && (
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-ink/40 mb-2">
            核心收获 Takeaways
          </p>
          <ul className="space-y-1.5">
            {summary.takeaways.map((t, i) => (
              <li key={i} className="flex gap-2 text-sm text-ink/80 leading-relaxed">
                <span className="text-pine flex-shrink-0">✓</span>
                <span>{t}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {summary.source_url && (
        <a
          href={summary.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-block text-[11px] text-ink/40 hover:text-teal transition-colors break-all"
        >
          🔗 {summary.source_url}
        </a>
      )}
    </div>
  );
}
