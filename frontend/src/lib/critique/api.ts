import { API_BASE } from "@/lib/api";

// ── Types ────────────────────────────────────────────────────────────────────

export type Dimension = {
  label: string;
  score: number;
  critique: string;
  suggestions: string[];
};

export type Evaluation = {
  overall: {
    band: string;
    summary: string;
    top_fix: string;
  };
  dimensions: Dimension[];
};

export type Verdict = {
  better: boolean;
  reason: string;
  dimensions_improved: string[];
};

export type Revision = {
  revised: string;
  changes: string[];
  verdict: Verdict;
};

// ── Helpers ──────────────────────────────────────────────────────────────────

async function handleError(res: Response, fallback: string): Promise<never> {
  const body = await res.json().catch(() => null) as { detail?: unknown } | null;
  const detail = typeof body?.detail === "string" ? body.detail : undefined;
  throw new Error(detail ?? fallback);
}

// Defense-in-depth: a tool-call response can occasionally arrive with a nested
// field serialized as a JSON string instead of a real array/object. Coerce so
// the UI's .map() never crashes the page (the backend also normalizes this).
function asArray<T = unknown>(v: unknown): T[] {
  if (Array.isArray(v)) return v as T[];
  if (typeof v === "string") {
    try {
      const parsed = JSON.parse(v);
      if (Array.isArray(parsed)) return parsed as T[];
    } catch {
      /* not JSON — fall through */
    }
  }
  return [];
}

function asObject(v: unknown): Record<string, unknown> {
  if (v && typeof v === "object" && !Array.isArray(v)) return v as Record<string, unknown>;
  if (typeof v === "string") {
    try {
      const parsed = JSON.parse(v);
      if (parsed && typeof parsed === "object") return parsed as Record<string, unknown>;
    } catch {
      /* ignore */
    }
  }
  return {};
}

function normalizeEvaluation(raw: unknown): Evaluation {
  const r = (raw ?? {}) as Record<string, unknown>;
  const overall = asObject(r.overall);
  return {
    overall: {
      band: String(overall.band ?? ""),
      summary: String(overall.summary ?? ""),
      top_fix: String(overall.top_fix ?? ""),
    },
    dimensions: asArray<Record<string, unknown>>(r.dimensions).map((d) => ({
      label: String(d.label ?? ""),
      score: Number(d.score ?? 0),
      critique: String(d.critique ?? ""),
      suggestions: asArray<string>(d.suggestions).map((s) => String(s)),
    })),
  };
}

function normalizeRevision(raw: unknown): Revision {
  const r = (raw ?? {}) as Record<string, unknown>;
  const verdict = asObject(r.verdict);
  return {
    revised: String(r.revised ?? ""),
    changes: asArray<string>(r.changes).map((c) => String(c)),
    verdict: {
      better: Boolean(verdict.better),
      reason: String(verdict.reason ?? ""),
      dimensions_improved: asArray<string>(verdict.dimensions_improved).map((d) => String(d)),
    },
  };
}

// ── API Functions ─────────────────────────────────────────────────────────────

/**
 * Upload a .docx/.pdf/.md/.txt file and extract its text content.
 * Returns { text, filename } on success.
 */
export async function extractFile(
  file: File,
): Promise<{ text: string; filename: string }> {
  const form = new FormData();
  form.append("file", file);

  const res = await fetch(`${API_BASE}/critique/extract`, {
    method: "POST",
    body: form,
    cache: "no-store",
  });

  if (!res.ok) {
    await handleError(res, "解析失败");
  }

  return res.json() as Promise<{ text: string; filename: string }>;
}

/**
 * Send extracted text + paper type + output language for evaluation.
 * Returns a full Evaluation object on success.
 */
export async function evaluateEssay(
  text: string,
  paperType: string,
  outputLang: string,
): Promise<Evaluation> {
  const res = await fetch(`${API_BASE}/critique/evaluate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, paper_type: paperType, output_lang: outputLang }),
    cache: "no-store",
  });

  if (!res.ok) {
    await handleError(res, "评估失败");
  }

  return normalizeEvaluation(await res.json());
}

/**
 * Send text for a single-round AI-assisted revision.
 * Returns a Revision object (revised text + changes list + verdict).
 * Caps at ~15 000 chars; backend returns 422 with a message if exceeded.
 */
export async function reviseEssay(
  text: string,
  paperType: string,
  outputLang: string,
): Promise<Revision> {
  const res = await fetch(`${API_BASE}/critique/revise`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, paper_type: paperType, output_lang: outputLang }),
    cache: "no-store",
  });

  if (!res.ok) {
    await handleError(res, "改进失败");
  }

  return normalizeRevision(await res.json());
}
