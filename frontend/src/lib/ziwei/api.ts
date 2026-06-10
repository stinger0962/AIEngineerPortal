import { API_BASE } from "@/lib/api";
import type { ZiweiChart } from "./types";

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
    throw new Error(`Request failed: ${response.status}`);
  }
  return (await response.json()) as T;
}

export const ziweiApi = {
  listProfiles: () => request<ZiweiProfileOut[]>("/ziwei/profiles"),
  createProfile: (payload: ZiweiProfileCreate) =>
    request<ZiweiProfileOut>("/ziwei/profiles", { method: "POST", body: JSON.stringify(payload) }),
  updateProfile: (id: number, payload: Partial<ZiweiProfileCreate> & { persona?: string }) =>
    request<ZiweiProfileOut>(`/ziwei/profiles/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteProfile: (id: number) =>
    request<{ deleted: number }>(`/ziwei/profiles/${id}`, { method: "DELETE" }),
};
