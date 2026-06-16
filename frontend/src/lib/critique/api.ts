import { API_BASE } from "@/lib/api";

// ── Types ────────────────────────────────────────────────────────────────────

export type PatchEdit = {
  find: string;
  replace: string;
  reason: string;
};

export type Patch = {
  patched: string;
  summary: string;
  applied: PatchEdit[];
  unapplied: PatchEdit[];
  notes: string[];
};

export type DimensionLayer = "writing" | "substance";

export type Dimension = {
  label: string;
  layer: DimensionLayer;
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

export type Finding = {
  category: string;
  severity: string;
  location: string;
  issue: string;
  recommendation: string;
};

export type DocReview = {
  summary: string;
  findings: Finding[];
};

export type ProbeQuestion = {
  location: string;
  weakness: string;
  question: string;
};

export type ProbeStance = "evidence" | "speculation" | "skip";

export type ProbeAnswerInput = {
  question: string;
  answer: string;
  stance: ProbeStance;
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
    dimensions: asArray<Record<string, unknown>>(r.dimensions).map((d) => {
      const label = String(d.label ?? "");
      let layer = String(d.layer ?? "").toLowerCase();
      if (layer !== "writing" && layer !== "substance") {
        // Fallback: classify by label keyword (substance = rigor / originality).
        layer = /严谨|rigor|原创|贡献|originality|contribution/i.test(label)
          ? "substance"
          : "writing";
      }
      return {
        label,
        layer: layer as DimensionLayer,
        score: Number(d.score ?? 0),
        critique: String(d.critique ?? ""),
        suggestions: asArray<string>(d.suggestions).map((s) => String(s)),
      };
    }),
  };
}

function normalizeDocReview(raw: unknown): DocReview {
  const r = (raw ?? {}) as Record<string, unknown>;
  return {
    summary: String(r.summary ?? ""),
    findings: asArray<Record<string, unknown>>(r.findings).map((f) => ({
      category: String(f.category ?? ""),
      severity: String(f.severity ?? ""),
      location: String(f.location ?? ""),
      issue: String(f.issue ?? ""),
      recommendation: String(f.recommendation ?? ""),
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

function normalizeProbe(raw: unknown): ProbeQuestion[] {
  const r = (raw ?? {}) as Record<string, unknown>;
  return asArray<Record<string, unknown>>(r.questions).map((q) => ({
    location: String(q.location ?? ""),
    weakness: String(q.weakness ?? ""),
    question: String(q.question ?? ""),
  }));
}

function normalizePatch(raw: unknown): Patch {
  const r = (raw ?? {}) as Record<string, unknown>;
  const normEdit = (e: Record<string, unknown>): PatchEdit => ({
    find: String(e.find ?? ""),
    replace: String(e.replace ?? ""),
    reason: String(e.reason ?? ""),
  });
  return {
    patched: String(r.patched ?? ""),
    summary: String(r.summary ?? ""),
    applied: asArray<Record<string, unknown>>(r.applied).map(normEdit),
    unapplied: asArray<Record<string, unknown>>(r.unapplied).map(normEdit),
    notes: asArray<string>(r.notes).map((n) => String(n)),
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
 * Send full paper text for document-level review.
 * Returns a DocReview object (summary + findings list).
 * Handles up to ~60 000 chars; no length cap on the frontend.
 */
export async function docReview(
  text: string,
  paperType: string,
  outputLang: string,
): Promise<DocReview> {
  const res = await fetch(`${API_BASE}/critique/docreview`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, paper_type: paperType, output_lang: outputLang }),
    cache: "no-store",
  });

  if (!res.ok) {
    await handleError(res, "审阅失败");
  }

  return normalizeDocReview(await res.json());
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

/**
 * Send text for patch-style improvement (find/replace edits applied in place).
 * Returns a Patch object: full improved text + applied/unapplied edit list + notes.
 * No character cap — handles up to ~60 000 chars.
 */
export async function patchEssay(
  text: string,
  paperType: string,
  outputLang: string,
): Promise<Patch> {
  const res = await fetch(`${API_BASE}/critique/patch`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, paper_type: paperType, output_lang: outputLang, depth: "medium" }),
    cache: "no-store",
  });

  if (!res.ok) {
    await handleError(res, "改进失败");
  }

  return normalizePatch(await res.json());
}

/**
 * 深挖实质 step 1: get targeted probe questions on the paper's substance-layer
 * weaknesses (rigor / originality). No character cap (handles up to ~60 000 chars).
 */
export async function probeEssay(
  text: string,
  paperType: string,
  outputLang: string,
): Promise<ProbeQuestion[]> {
  const res = await fetch(`${API_BASE}/critique/probe`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, paper_type: paperType, output_lang: outputLang }),
    cache: "no-store",
  });

  if (!res.ok) {
    await handleError(res, "提问失败");
  }

  return normalizeProbe(await res.json());
}

/**
 * 深挖实质 step 2: weave the author's answers into the paper. Returns a Patch object
 * (full updated text + applied/unapplied edits + notes). Never fabricates.
 */
export async function integrateAnswers(
  text: string,
  answers: ProbeAnswerInput[],
  paperType: string,
  outputLang: string,
): Promise<Patch> {
  const res = await fetch(`${API_BASE}/critique/integrate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, paper_type: paperType, output_lang: outputLang, answers }),
    cache: "no-store",
  });

  if (!res.ok) {
    await handleError(res, "融入失败");
  }

  return normalizePatch(await res.json());
}
