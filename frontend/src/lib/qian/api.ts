import { paidProduct } from "@/lib/product/config";
import { paidRequestHeaders, paidRequestOptions, invalidatePaidSession } from "@/lib/product/account";
import { API_BASE } from "@/lib/api";
import { getDeviceId } from "@/lib/deviceId";
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

export type QianReadingDetail = { id: number; question: string; sign_id: number; grade: string; response: string; created_at: string | null };

export type QianReadingOut = { id: number; question: string; sign_id: number; grade: string; created_at: string | null };

async function streamOracle(
  body: { question: string; sign_id?: number },
  handlers: QianStreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${API_BASE}/qian/oracle/stream`, {
    method: "POST", headers: { "Content-Type": "application/json", ...(paidProduct ? paidRequestHeaders() : { "X-Device-Id": getDeviceId() }) },
    body: JSON.stringify(body), cache: "no-store", ...paidRequestOptions(), signal,
  });
  if (!res.ok || !res.body) {
    if (res.status === 401) invalidatePaidSession();
    const err = (await res.json().catch(() => null)) as { detail?: unknown } | null;
    throw new QianApiError(res.status, typeof err?.detail === "string" ? err.detail : undefined);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let terminal = false;
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
      if (!ev || typeof ev !== "object" || terminal) continue;
      if (ev.type === "sign") handlers.onSign(ev.sign as QianSign);
      else if (ev.type === "text") handlers.onText(ev.delta as string);
      else if (ev.type === "camera") handlers.onCamera(ev.command as CameraCommand);
      else if (ev.type === "done") {
        terminal = true;
        handlers.onDone((ev.meta as { model?: string; total_tokens?: number }) ?? {});
      } else if (ev.type === "error") {
        terminal = true;
        handlers.onError();
      }
    }
  }
  // Closing the HTTP stream is not a successful reading. Release the narration
  // queue on truncated SSE so the workspace can leave its reading/shaking phase.
  if (!terminal && !signal?.aborted) handlers.onError();
}

export const qianApi = {
  streamOracle,
  getReading: async (id: number, signal?: AbortSignal): Promise<QianReadingDetail> => {
    if (!Number.isSafeInteger(id) || id < 1) throw new QianApiError(400, "Invalid reading");
    const response = await fetch(`${API_BASE}/qian/readings/${id}`, {
      cache: "no-store", ...paidRequestOptions(), signal,
      headers: { ...(paidProduct ? paidRequestHeaders() : { "X-Device-Id": getDeviceId() }) },
    });
    if (!response.ok) {
      if (response.status === 401) invalidatePaidSession();
      throw new QianApiError(response.status);
    }
    const result = await response.json() as QianReadingDetail;
    if (!result || result.id !== id || typeof result.question !== "string" || typeof result.response !== "string"
        || !Number.isSafeInteger(result.sign_id) || result.sign_id < 1 || typeof result.grade !== "string"
        || (result.created_at !== null && typeof result.created_at !== "string")) throw new QianApiError(502, "Invalid reading response");
    return result;
  },
  listReadings: (signal?: AbortSignal) =>
    fetch(`${API_BASE}/qian/readings`, { signal, cache: "no-store", ...paidRequestOptions(), headers: { ...(paidProduct ? paidRequestHeaders() : { "X-Device-Id": getDeviceId() }) } })
      .then(async (r) => {
        if (!r.ok) { if (r.status === 401) invalidatePaidSession(); throw new QianApiError(r.status); }
        const rows = await r.json() as QianReadingOut[];
        if (!Array.isArray(rows) || rows.some(row => !row || !Number.isSafeInteger(row.id) || row.id < 1
          || !Number.isSafeInteger(row.sign_id) || row.sign_id < 1 || typeof row.question !== "string"
          || typeof row.grade !== "string" || (row.created_at !== null && typeof row.created_at !== "string"))) {
          throw new QianApiError(502, "Invalid reading history");
        }
        return rows;
      }),
};
