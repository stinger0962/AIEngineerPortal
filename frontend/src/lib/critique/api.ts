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

// ── Helpers ──────────────────────────────────────────────────────────────────

async function handleError(res: Response, fallback: string): Promise<never> {
  const body = await res.json().catch(() => null) as { detail?: unknown } | null;
  const detail = typeof body?.detail === "string" ? body.detail : undefined;
  throw new Error(detail ?? fallback);
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
 * Send extracted text + paper type for evaluation.
 * Returns a full Evaluation object on success.
 */
export async function evaluateEssay(
  text: string,
  paperType: string,
): Promise<Evaluation> {
  const res = await fetch(`${API_BASE}/critique/evaluate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, paper_type: paperType }),
    cache: "no-store",
  });

  if (!res.ok) {
    await handleError(res, "评估失败");
  }

  return res.json() as Promise<Evaluation>;
}
