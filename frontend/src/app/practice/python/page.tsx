import Link from "next/link";

import { Panel } from "@/components/ui/panel";
import { SectionHeading } from "@/components/ui/section-heading";
import { portalApi } from "@/lib/api/portal";
import { titleCase } from "@/lib/utils";

const DIFFICULTY_COLORS: Record<string, string> = {
  easy: "bg-mint text-pine",
  beginner: "bg-mint text-pine",
  medium: "bg-sand text-ink",
  intermediate: "bg-sand text-ink",
  hard: "bg-ember/15 text-ember",
  advanced: "bg-ember/15 text-ember",
};

const CATEGORY_COLORS: Record<string, string> = {
  "python-refresh": "border-l-pine",
  "data-transformation": "border-l-[#6366f1]",
  "api-async": "border-l-[#0ea5e9]",
  "prompt-formatting": "border-l-ember",
  retrieval: "border-l-[#8b5cf6]",
  evaluation: "border-l-[#10b981]",
  agents: "border-l-[#f43f5e]",
};

function extractSummary(promptMd: string): string {
  // Get first meaningful sentence from the markdown, skip headings
  const lines = promptMd.split("\n").filter((l) => l.trim() && !l.startsWith("#") && !l.startsWith("```"));
  const first = lines[0] || "";
  // Truncate to ~120 chars at word boundary
  if (first.length <= 120) return first;
  return first.slice(0, 120).replace(/\s+\S*$/, "") + "...";
}

export default async function PracticePage() {
  const exercises = await portalApi.getExercises();

  // Group by category
  const grouped = exercises.reduce(
    (acc, ex) => {
      const cat = ex.category || "other";
      if (!acc[cat]) acc[cat] = [];
      acc[cat].push(ex);
      return acc;
    },
    {} as Record<string, typeof exercises>,
  );

  return (
    <div className="space-y-8">
      <SectionHeading
        eyebrow="Practice"
        title="Hands-on drills tuned for AI engineering."
        description="Build implementation muscle memory. Each exercise includes starter code, a reference solution, and AI-powered feedback."
      />

      {Object.entries(grouped).map(([category, exs]) => (
        <div key={category}>
          <h2 className="mb-4 text-xs font-semibold uppercase tracking-[0.28em] text-ember">
            {titleCase(category)} ({exs.length})
          </h2>
          <div className="grid gap-4 xl:grid-cols-2 lg:grid-cols-1">
            {exs.map((exercise) => (
              <Link key={exercise.id} href={`/practice/python/${exercise.id}`}>
                <Panel
                  className={`flex items-start gap-4 border-l-4 ${CATEGORY_COLORS[exercise.category] || "border-l-ink/20"} hover:shadow-lg transition-all cursor-pointer h-full`}
                >
                  <div className="flex-1 min-w-0 space-y-2">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="font-display text-lg text-ink leading-snug">{exercise.title}</h3>
                      {exercise.is_generated && (
                        <span className="text-[10px] bg-ember/10 text-ember px-2 py-0.5 rounded-full font-medium">
                          AI Generated
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-ink/60 line-clamp-2">{extractSummary(exercise.prompt_md)}</p>
                    {exercise.tags_json?.length ? (
                      <div className="flex gap-1.5 flex-wrap">
                        {exercise.tags_json.slice(0, 3).map((tag) => (
                          <span key={tag} className="text-[10px] text-ink/40 bg-ink/5 px-2 py-0.5 rounded-full">
                            {tag}
                          </span>
                        ))}
                      </div>
                    ) : null}
                  </div>
                  <span
                    className={`shrink-0 rounded-full px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] ${DIFFICULTY_COLORS[exercise.difficulty] || "bg-sand text-ink"}`}
                  >
                    {exercise.difficulty}
                  </span>
                </Panel>
              </Link>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
