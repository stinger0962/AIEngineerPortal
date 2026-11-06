import { API_BASE } from "@/lib/api";
import { getDeviceId, setDeviceId } from "@/lib/deviceId";

// Recovery must still work when old localStorage is corrupt or unavailable.
export function recoveryDeviceId(): string {
  const value = getDeviceId();
  return value.length <= 64 && /^[\x20-\x7e\x80-\xff]*$/.test(value) ? value : "";
}

export const recoveryEnabled = process.env.NEXT_PUBLIC_ACCOUNT_RECOVERY === "true";
export async function accountRequest<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`${API_BASE}/account${path}`, {
    method: body === undefined ? "GET" : "POST",
    headers: { "Content-Type": "application/json", "X-Recovery-Client": "1", "X-Device-Id": recoveryDeviceId() },
    credentials: "include", cache: "no-store",
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  if (!response.ok) {
    const messages: Record<number, string> = {
      400: "验证码无效或已过期，请重新获取。",
      401: "登录已过期，请通过邮箱重新找回。",
      409: "此账号或邮箱已绑定，不能合并。请使用找回账号。",
      429: "尝试次数过多，请一小时后重试。",
      503: "邮件服务暂不可用，请稍后重试。",
    };
    throw new Error(messages[response.status] ?? "操作失败，请重试。");
  }
  return response.json() as Promise<T>;
}


export async function restoreLegacyDevice(code: string): Promise<void> {
  const clean = code.trim();
  if (!clean || clean.length > 64 || !/^[\x20-\x7e\x80-\xff]+$/.test(clean)) {
    throw new Error("旧设备找回码无效。");
  }
  // Recheck immediately before changing shared Ziwei/Qian browser identity.
  const session = await accountRequest<{ authenticated: boolean }>("/session");
  if (session.authenticated) throw new Error("请先退出邮箱账号，再恢复旧设备身份。");
  if (!setDeviceId(clean)) throw new Error("浏览器无法保存找回码，请检查存储设置。");
}
