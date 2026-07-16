// Anonymous per-browser identity for 命理 (紫微/灵签) — the site has no login, so
// each browser gets a random device id (its "找回码"). Sent as X-Device-Id on all
// 紫微/灵签 requests; the backend scopes profiles/readings to it. Persisted in
// localStorage so it survives refresh / leaving / VPN toggle. Save it to restore
// access on another browser (paste via setDeviceId).

const KEY = "oracle_device_id";

export function getDeviceId(): string {
  if (typeof window === "undefined") return "";
  try {
    let id = localStorage.getItem(KEY);
    if (!id) {
      id =
        typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
          ? crypto.randomUUID()
          : `dev-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`;
      localStorage.setItem(KEY, id);
    }
    return id;
  } catch {
    return "";
  }
}

/** Restore access on a new browser: overwrite the local device id with a saved 找回码. */
export function setDeviceId(id: string): boolean {
  if (typeof window === "undefined") return false;
  const clean = (id || "").trim();
  if (!clean || clean.length > 64) return false;
  try {
    localStorage.setItem(KEY, clean);
    return true;
  } catch {
    return false;
  }
}
