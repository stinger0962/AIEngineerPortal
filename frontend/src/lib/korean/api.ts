import { API_BASE } from "@/lib/api";
import type { MapRegion, NodeDetail } from "./types";

export class KoreanApiError extends Error {
  constructor(public status: number, detail?: string) {
    super(detail ?? `Request failed: ${status}`);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    const err = (await res.json().catch(() => null)) as { detail?: unknown } | null;
    throw new KoreanApiError(res.status, typeof err?.detail === "string" ? err.detail : undefined);
  }
  return (await res.json()) as T;
}

export type BossStreamHandlers = {
  onText: (delta: string) => void;
  onDone: (conversationId: number, goalMet: boolean) => void;
  onError: () => void;
};

async function streamBoss(
  slug: string,
  body: { message: string; conversation_id?: number },
  handlers: BossStreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${API_BASE}/korean/nodes/${slug}/boss`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
    signal,
  });
  if (!res.ok || !res.body) {
    handlers.onError();
    return;
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done || signal?.aborted) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed.startsWith("data:")) continue;
      const raw = trimmed.slice(5).trim();
      if (!raw) continue;
      let ev: { type: string; delta?: string; conversation_id?: number; goal_met?: boolean };
      try {
        ev = JSON.parse(raw);
      } catch {
        continue;
      }
      if (ev.type === "text" && ev.delta) handlers.onText(ev.delta);
      else if (ev.type === "done") handlers.onDone(ev.conversation_id ?? 0, Boolean(ev.goal_met));
      else if (ev.type === "error") handlers.onError();
    }
  }
}

export const koreanApi = {
  getMap: () => request<MapRegion[]>("/korean/map"),
  getNode: (slug: string) => request<NodeDetail>(`/korean/nodes/${slug}`),
  completeNode: (slug: string, score: number, stars: number) =>
    request<{ slug: string; status: string; stars: number }>(
      `/korean/nodes/${slug}/complete`,
      { method: "POST", body: JSON.stringify({ score, stars }) },
    ),
  resetProgress: () => request<{ deleted_progress: number }>("/korean/progress", { method: "DELETE" }),
  ttsUrl: () => `${API_BASE}/korean/tts`,
  streamBoss,
};
