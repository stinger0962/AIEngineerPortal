import Link from "next/link";
import { Briefcase, ExternalLink, Github, Plus } from "lucide-react";

import { ProjectEditor } from "@/components/forms/project-editor";
import { Panel } from "@/components/ui/panel";
import { portalApi } from "@/lib/api/portal";

const STATUS_COLORS: Record<string, string> = {
  planning: "bg-sand text-ink/60",
  "in-progress": "bg-ember/10 text-ember",
  complete: "bg-mint text-pine",
  shipped: "bg-pine/10 text-pine",
};

const CATEGORY_BORDERS: Record<string, string> = {
  "rag-app": "border-l-[#8b5cf6]",
  "agent-system": "border-l-[#f43f5e]",
  "eval-tooling": "border-l-[#10b981]",
};

export default async function ProjectsPage() {
  const projects = await portalApi.getProjects();

  return (
    <div className="space-y-6">
      {/* Hero */}
      <div className="relative overflow-hidden rounded-[28px] bg-gradient-to-br from-ink via-ink/95 to-pine p-8 text-cream">
        <div className="absolute top-0 right-0 w-64 h-64 bg-ember/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/4" />
        <div className="relative space-y-3">
          <div className="flex items-center gap-2">
            <Briefcase size={16} className="text-ember" />
            <span className="text-xs font-semibold uppercase tracking-[0.28em] text-ember">Portfolio</span>
          </div>
          <h1 className="font-display text-3xl lg:text-4xl leading-tight">Projects are what get you hired.</h1>
          <p className="text-cream/60 text-[15px] leading-7 max-w-2xl">
            Document what you built, the architecture decisions, and the lessons learned.
            This is your interview evidence — not just what you know, but what you&apos;ve shipped.
          </p>
          <div className="flex gap-4 pt-2 text-sm text-cream/50">
            <span>{projects.length} projects tracked</span>
            <span>{projects.filter((p) => p.status === "complete" || p.status === "shipped").length} completed</span>
          </div>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.3fr_0.7fr]">
        {/* Project cards */}
        <div className="space-y-4">
          {projects.length === 0 && (
            <Panel className="text-center py-12">
              <Briefcase size={32} className="mx-auto text-ink/20 mb-3" />
              <p className="text-ink/50">No projects yet. Add your first build below.</p>
            </Panel>
          )}
          {projects.map((project) => (
            <Link key={project.id} href={`/projects/${project.slug}`}>
              <Panel className={`border-l-4 ${CATEGORY_BORDERS[project.category] || "border-l-ink/20"} hover:shadow-lg transition-shadow cursor-pointer space-y-3`}>
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-1">
                    <h3 className="font-display text-xl text-ink">{project.title}</h3>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={`text-[10px] uppercase tracking-wide px-2 py-0.5 rounded-full font-semibold ${STATUS_COLORS[project.status] || "bg-sand text-ink/60"}`}>
                        {project.status}
                      </span>
                      <span className="text-[10px] text-ink/40 uppercase tracking-wide">{project.category?.replace(/-/g, " ")}</span>
                    </div>
                  </div>
                  <div className="shrink-0 text-center">
                    <p className="text-2xl font-bold text-ink">{project.portfolio_score}</p>
                    <p className="text-[10px] uppercase tracking-wide text-ink/40">Score</p>
                  </div>
                </div>
                <p className="text-sm text-ink/60 line-clamp-2">{project.summary}</p>
                {(project.repo_url || project.demo_url) && (
                  <div className="flex gap-3 pt-1">
                    {project.repo_url && (
                      <span className="flex items-center gap-1 text-xs text-ink/40">
                        <Github size={12} /> Repo
                      </span>
                    )}
                    {project.demo_url && (
                      <span className="flex items-center gap-1 text-xs text-ink/40">
                        <ExternalLink size={12} /> Live
                      </span>
                    )}
                  </div>
                )}
              </Panel>
            </Link>
          ))}
        </div>

        {/* Add project form */}
        <div>
          <Panel className="space-y-4 sticky top-6">
            <div className="flex items-center gap-2">
              <Plus size={16} className="text-ember" />
              <h2 className="text-xs font-semibold uppercase tracking-[0.28em] text-ember">Add Project</h2>
            </div>
            <p className="text-sm text-ink/50">Even rough notes help build your portfolio story. You can refine later.</p>
            <ProjectEditor />
          </Panel>
        </div>
      </div>
    </div>
  );
}
