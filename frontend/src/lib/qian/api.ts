import { API_BASE } from "@/lib/api";
import type { CameraCommand } from "@/lib/ziwei/api";

export class QianApiError extends Error {
  constructor(public status: number, detail?: string) { super(detail ?? `Request failed: ${status}`); }
}

export type QianSign = {
  id: number; grade: string; palace: string; title: string;
  poetry: string; meaning: string; holy: string;
};

export type QianStreamHandlers = {
  onSign: (sign: QianSign) => void;
  onText: (delta: string) => void;
  onCamera: (command: CameraCommand) => void;
  onDone: (meta: { model?: string; total_tokens?: number }) => void;
  onError: () => void;
};

export type QianReadingOut = { id: number; question: string; sign_id: number; grade: string; created_at: string | null };

async function streamOracle(
  body: { question: string; sign_id?: number },
  handlers: QianStreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${API_BASE}/qian/oracle/stream`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body), cache: "no-store", signal,
  });
  if (!res.ok || !res.body) {
    const err = (await res.json().catch(() => null)) as { detail?: unknown } | null;
    throw new QianApiError(res.status, typeof err?.detail === "string" ? err.detail : undefined);
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
      const t = line.trim();
      if (!t.startsWith("data:")) continue;
      const raw = t.slice(5).trim();
      if (!raw) continue;
      let ev: { type: string; [k: string]: unknown };
      try { ev = JSON.parse(raw); } catch { continue; }
      if (ev.type === "sign") handlers.onSign(ev.sign as QianSign);
      else if (ev.type === "text") handlers.onText(ev.delta as string);
      else if (ev.type === "camera") handlers.onCamera(ev.command as CameraCommand);
      else if (ev.type === "done") handlers.onDone((ev.meta as { model?: string; total_tokens?: number }) ?? {});
      else if (ev.type === "error") handlers.onError();
    }
  }
}

export const qianApi = {
  streamOracle,
  listReadings: () => fetch(`${API_BASE}/qian/readings`, { cache: "no-store" }).then((r) => r.json() as Promise<QianReadingOut[]>),
};
