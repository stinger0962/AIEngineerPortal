import { API_BASE } from "@/lib/api";
import { getDeviceId } from "@/lib/deviceId";
import type { ZiweiChart } from "./types";

/** HTTP 层错误（区别于排盘错误），携带状态码与后端 detail */
export class ZiweiApiError extends Error {
  constructor(
    public status: number,
    detail?: string,
  ) {
    super(detail ?? `Request failed: ${status}`);
  }
}

export type ZiweiProfileOut = {
  id: number;
  name: string;
  relation: string;
  gender: string;
  birth_date: string;
  birth_time_index: number;
  is_lunar_input: boolean;
  is_leap_month: boolean;
  chart_json: ZiweiChart | Record<string, never>;
  persona: string;
  created_at: string | null;
  updated_at: string | null;
};

export type ZiweiProfileCreate = {
  name: string;
  relation: string;
  gender: string;
  birth_date: string;
  birth_time_index: number;
  is_lunar_input: boolean;
  is_leap_month: boolean;
  chart_json: ZiweiChart;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", "X-Device-Id": getDeviceId(), ...(init?.headers ?? {}) },
    cache: "no-store",
  });
  if (!response.ok) {
    const err = await response.json().catch(() => null) as { detail?: unknown } | null;
    throw new ZiweiApiError(response.status, typeof err?.detail === "string" ? err.detail : undefined);
  }
  return (await response.json()) as T;
}

/** chart_json 非空守卫（后端对缺失数据返回空对象） */
export function hasChart(profile: ZiweiProfileOut): profile is ZiweiProfileOut & { chart_json: ZiweiChart } {
  return "palaces" in profile.chart_json;
}

export type CameraCommand =
  | { type: "focus_palace"; palace: string }
  | { type: "overview" }
  | { type: "explain_term"; term: string; explanation: string };

export type OracleSegment = { text: string; commands: CameraCommand[] };

export type OracleReply = {
  conversation_id: number;
  response: string;
  camera_commands: CameraCommand[];
  segments: OracleSegment[];
  meta: { model?: string; total_tokens?: number; latency_ms?: number; rounds?: number };
};

export type ConversationOut = { id: number; scenario: string; title: string; created_at: string | null };
export type MessageOut = {
  id: number;
  role: string;
  content: string;
  chart_context_json: { camera_commands?: CameraCommand[]; segments?: OracleSegment[]; scenario?: string };
  created_at: string | null;
};

export type OracleAsk = { scenario: string; message: string; conversation_id?: number };

/** 流式解盘的 SSE 事件 */
export type OracleStreamEvent =
  | { type: "text"; delta: string }
  | { type: "camera"; command: CameraCommand }
  | { type: "done"; conversation_id: number; meta: OracleReply["meta"] }
  | { type: "error" };

export type OracleStreamHandlers = {
  onText: (delta: string) => void;
  onCamera: (command: CameraCommand) => void;
  onDone: (conversationId: number, meta: OracleReply["meta"]) => void;
  onError: () => void;
};

/** 流式解盘：text 增量逐字铺、camera 即时触发镜头/术语、done 落定会话、error 标记失败。
 * 校验类错误（404/400/429/503）在开流前以 ZiweiApiError 抛出，由调用方本地化提示。 */
async function streamOracle(
  profileId: number,
  body: OracleAsk,
  handlers: OracleStreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(`${API_BASE}/ziwei/profiles/${profileId}/oracle/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Device-Id": getDeviceId() },
    body: JSON.stringify(body),
    cache: "no-store",
    signal,
  });
  if (!response.ok || !response.body) {
    const err = (await response.json().catch(() => null)) as { detail?: unknown } | null;
    throw new ZiweiApiError(response.status, typeof err?.detail === "string" ? err.detail : undefined);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done || signal?.aborted) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? ""; // 末行可能是半截，留到下次
    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed.startsWith("data:")) continue; // 跳过 ping 注释行 (": ...") 与空行
      const raw = trimmed.slice(5).trim();
      if (!raw) continue;
      let ev: OracleStreamEvent;
      try {
        ev = JSON.parse(raw) as OracleStreamEvent;
      } catch {
        continue; // 半截/畸形 SSE 行，忽略
      }
      if (ev.type === "text") handlers.onText(ev.delta);
      else if (ev.type === "camera") handlers.onCamera(ev.command);
      else if (ev.type === "done") handlers.onDone(ev.conversation_id, ev.meta);
      else if (ev.type === "error") handlers.onError();
    }
  }
}

export const ziweiApi = {
  listProfiles: () => request<ZiweiProfileOut[]>("/ziwei/profiles"),
  createProfile: (payload: ZiweiProfileCreate) =>
    request<ZiweiProfileOut>("/ziwei/profiles", { method: "POST", body: JSON.stringify(payload) }),
  updateProfile: (id: number, payload: Partial<ZiweiProfileCreate> & { persona?: string }) =>
    request<ZiweiProfileOut>(`/ziwei/profiles/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteProfile: (id: number) =>
    request<{ deleted: number }>(`/ziwei/profiles/${id}`, { method: "DELETE" }),
  askOracle: (profileId: number, body: OracleAsk) =>
    request<OracleReply>(`/ziwei/profiles/${profileId}/oracle`, { method: "POST", body: JSON.stringify(body) }),
  streamOracle,
  listConversations: (profileId: number) =>
    request<ConversationOut[]>(`/ziwei/profiles/${profileId}/conversations`),
  listMessages: (conversationId: number) =>
    request<MessageOut[]>(`/ziwei/conversations/${conversationId}/messages`),
  /** 一次性认领无归属旧数据（紫微档案 + 灵签记录）到本浏览器，需服务器口令。 */
  claimLegacy: (code: string) =>
    request<{ claimed_profiles: number; claimed_readings: number }>("/ziwei/claim", {
      method: "POST",
      body: JSON.stringify({ code }),
    }),
};
