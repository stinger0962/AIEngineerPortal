import { API_BASE } from "@/lib/api";
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
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
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

export type OracleReply = {
  conversation_id: number;
  response: string;
  camera_commands: CameraCommand[];
  meta: { model?: string; total_tokens?: number; latency_ms?: number; rounds?: number };
};

export type OracleAsk = { scenario: string; message: string; conversation_id?: number };

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
};
