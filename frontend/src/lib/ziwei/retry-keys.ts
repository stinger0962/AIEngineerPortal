// Request keys are not credentials. Tab storage retains uncertain requests across navigation.
export function createRetryKeys(storage?: Pick<Storage, "getItem" | "setItem" | "removeItem">, uuid: () => string = () => crypto.randomUUID()) {
  const memory = new Map<string, { payload: string; key: string }>();
  return {
    get(scope: string, payload: unknown): string {
      const fingerprint = JSON.stringify(payload);
      let current = memory.get(scope);
      try {
        const saved = storage?.getItem(`ziwei-request:${scope}`);
        if (saved) current = JSON.parse(saved);
      } catch { /* in-memory fallback */ }
      if (!current || current.payload !== fingerprint) current = { payload: fingerprint, key: uuid() };
      memory.set(scope, current);
      try { storage?.setItem(`ziwei-request:${scope}`, JSON.stringify(current)); } catch { /* in-memory fallback */ }
      return current.key;
    },
    complete(scope: string) {
      memory.delete(scope);
      try { storage?.removeItem(`ziwei-request:${scope}`); } catch { /* storage unavailable */ }
    },
  };
}
let storage: Storage | undefined;
try { if (typeof window !== "undefined") storage = window.sessionStorage; } catch { /* privacy mode */ }
export const retryKeys = createRetryKeys(storage);
