"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { accountRequest, type AccountSession } from "@/lib/product/account";
import { PaidAccountPanel } from "./account-panel";

export function PaidAccountGate({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<AccountSession | null>(null);
  const [checking, setChecking] = useState(true);
  const requestRef = useRef<AbortController | null>(null);
  const refresh = useCallback(() => {
    requestRef.current?.abort();
    const controller = new AbortController(); requestRef.current = controller;
    setChecking(true);
    accountRequest<AccountSession>("/session", undefined, controller.signal)
      .then(value => { if (!controller.signal.aborted) setSession(value); })
      .catch(() => { if (!controller.signal.aborted) setSession(null); })
      .finally(() => { if (!controller.signal.aborted) setChecking(false); });
  }, []);
  useEffect(() => {
    refresh();
    const visible = () => { if (document.visibilityState === "visible") refresh(); };
    const invalidate = () => { requestRef.current?.abort(); setSession(null); setChecking(false); };
    window.addEventListener("focus", refresh);
    window.addEventListener("pageshow", refresh);
    window.addEventListener("paid-account-changed", refresh);
    window.addEventListener("paid-session-invalid", invalidate);
    document.addEventListener("visibilitychange", visible);
    let channel: BroadcastChannel | undefined;
    try { channel = new BroadcastChannel("paid-account"); channel.onmessage = refresh; } catch { /* focus remains */ }
    return () => {
      requestRef.current?.abort(); channel?.close();
      window.removeEventListener("focus", refresh);
      window.removeEventListener("pageshow", refresh);
      window.removeEventListener("paid-account-changed", refresh);
      window.removeEventListener("paid-session-invalid", invalidate);
      document.removeEventListener("visibilitychange", visible);
    };
  }, [refresh]);
  const authenticated = session?.authenticated && session.enabled && Number.isInteger(session.account_id);
  return <>
    {checking && <p role="status" className="p-4 text-sm text-ink/65">正在检查登录状态…</p>}
    {authenticated ? <div key={session.account_id} hidden={checking}>{children}</div>
      : <div hidden={checking}><PaidAccountPanel onAuthenticated={refresh} /></div>}
  </>;
}
