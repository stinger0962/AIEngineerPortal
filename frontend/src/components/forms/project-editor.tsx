"use client";

import { useState } from "react";

import type { Project } from "@/lib/types/portal";
import { portalApi } from "@/lib/api/portal";

type ProjectPayload = Omit<Project, "id" | "slug"> & { title: string };

const initialState: ProjectPayload = {
  title: "",
  summary: "",
  status: "planned",
  category: "portfolio",
  stack_json: [],
  architecture_md: "",
  repo_url: null,
  demo_url: null,
  lessons_learned_md: "",
  portfolio_score: 70,
};

export function ProjectEditor({ initialProject }: { initialProject?: Project | null }) {
  const [form, setForm] = useState<ProjectPayload>(
    initialProject
      ? {
          title: initialProject.title,
          summary: initialProject.summary,
          status: initialProject.status,
          category: initialProject.category,
          stack_json: initialProject.stack_json,
          architecture_md: initialProject.architecture_md,
          repo_url: initialProject.repo_url,
          demo_url: initialProject.demo_url,
          lessons_learned_md: initialProject.lessons_learned_md,
          portfolio_score: initialProject.portfolio_score,
        }
      : initialState,
  );
  const [status, setStatus] = useState(initialProject ? "Update project" : "Create project");

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus("Saving...");
    if (initialProject) {
      await portalApi.updateProject(initialProject.id, form);
      setStatus("Updated");
      return;
    }
    await portalApi.createProject(form);
    setStatus("Created");
    setForm(initialState);
  }

  return (
    <form className="grid gap-4 md:grid-cols-2" onSubmit={onSubmit}>
      <input
        value={form.title}
        onChange={(event) => setForm({ ...form, title: event.target.value })}
        placeholder="Project title"
        className="rounded-2xl border border-ink/10 bg-white p-3 text-sm"
      />
      <input
        value={form.category}
        onChange={(event) => setForm({ ...form, category: event.target.value })}
        placeholder="Category"
        className="rounded-2xl border border-ink/10 bg-white p-3 text-sm"
      />
      <textarea
        value={form.summary}
        onChange={(event) => setForm({ ...form, summary: event.target.value })}
        placeholder="Project summary"
        className="min-h-28 rounded-2xl border border-ink/10 bg-white p-3 text-sm md:col-span-2"
      />
      <textarea
        value={form.architecture_md}
        onChange={(event) => setForm({ ...form, architecture_md: event.target.value })}
        placeholder="Architecture notes"
        className="min-h-28 rounded-2xl border border-ink/10 bg-white p-3 text-sm md:col-span-2"
      />
      <input
        value={form.status}
        onChange={(event) => setForm({ ...form, status: event.target.value })}
        placeholder="Status"
        className="rounded-2xl border border-ink/10 bg-white p-3 text-sm"
      />
      <input
        value={form.portfolio_score}
        onChange={(event) => setForm({ ...form, portfolio_score: Number(event.target.value) })}
        type="number"
        placeholder="Portfolio score"
        className="rounded-2xl border border-ink/10 bg-white p-3 text-sm"
      />
      <input
        value={form.stack_json.join(", ")}
        onChange={(event) =>
          setForm({
            ...form,
            stack_json: event.target.value
              .split(",")
              .map((item) => item.trim())
              .filter(Boolean),
          })
        }
        placeholder="Stack comma-separated"
        className="rounded-2xl border border-ink/10 bg-white p-3 text-sm md:col-span-2"
      />
      <button type="submit" className="rounded-full bg-ember px-5 py-3 text-sm font-semibold text-white md:col-span-2">
        {status}
      </button>
    </form>
  );
}
