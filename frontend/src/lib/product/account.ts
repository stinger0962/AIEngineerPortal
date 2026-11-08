import { API_BASE } from "@/lib/api";
import { paidProduct } from "./config";

/** Account sessions are host-only HttpOnly cookies, never browser-storage tokens. */
export const paidRequestOptions = (): RequestInit => paidProduct ? { credentials: "include" } : {};
export const paidRequestHeaders = (): Record<string, string> => paidProduct ? { "X-Paid-Client": "1" } : {};
export type AccountSession = { authenticated: boolean; enabled: boolean; account_id?: number | null };

export async function accountRequest<T>(path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_BASE}/account${path}`, {
    method: body === undefined ? "GET" : "POST",
    headers: { "Content-Type": "application/json", "X-Paid-Client": "1" },
    credentials: "include", cache: "no-store", signal,
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  if (!response.ok) {
    const messages: Record<number, string> = {
      400: "验证码无效或已过期，请重新获取。",
      401: "登录已过期，请清除本浏览器登录状态后重新登录。",
      403: "当前访问地址未获授权，请从正式网站重试。",
      409: "账号状态刚刚更新，请再次提交验证码。",
      429: "尝试次数过多，请稍后再试。",
      503: "邮箱登录尚未开放，请稍后再来。",
    };
    throw new Error(messages[response.status] ?? "操作失败，请重试。");
  }
  return response.json() as Promise<T>;
}

/** Remove retry references, not user records, when switching accounts. */
export function clearPaidRetryState() {
  if (typeof window === "undefined") return;
  try {
    for (let i = sessionStorage.length - 1; i >= 0; i--) {
      const key = sessionStorage.key(i);
      if (key?.startsWith("ziwei-request:") || key === "ziwei-selected-profile") sessionStorage.removeItem(key);
    }
  } catch { /* Authentication is independent of browser storage. */ }
}

/** Signals contain no identity or credentials. Recheck the server after a change. */
export function notifyPaidAccountChange() {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new Event("paid-account-changed"));
  try {
    const channel = new BroadcastChannel("paid-account");
    channel.postMessage("changed"); channel.close();
  } catch { /* Focus/pageshow revalidation remains available. */ }
}

export function invalidatePaidSession() {
  if (paidProduct && typeof window !== "undefined") window.dispatchEvent(new Event("paid-session-invalid"));
}
