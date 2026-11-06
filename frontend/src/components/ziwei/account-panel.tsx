"use client";

import { useEffect, useState } from "react";
import { accountRequest, restoreLegacyDevice } from "@/lib/ziwei/account";

export function AccountPanel() {
  const [email, setEmail] = useState("");
  const [purpose, setPurpose] = useState<"bind" | "recover">("recover");
  const [challenge, setChallenge] = useState("");
  const [code, setCode] = useState("");
  const [authenticated, setAuthenticated] = useState<boolean | null>(null);
  const [legacyCode, setLegacyCode] = useState("");
  const [legacyConsent, setLegacyConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  useEffect(() => {
    accountRequest<{ authenticated: boolean }>("/session").then(r => setAuthenticated(r.authenticated)).catch(() => {});
  }, []);
  async function run(action: () => Promise<void>) {
    setBusy(true); setMessage("");
    try { await action(); } catch (error) { setMessage(error instanceof Error ? error.message : "操作失败，请重试。"); }
    finally { setBusy(false); }
  }
  const reload = () => window.location.reload();
  return <section id="account-recovery" className="rounded-2xl border border-violet-200 bg-white p-4 text-sm text-ink shadow-sm" aria-label="邮箱账号">
    <h2 className="font-semibold">邮箱账号 · 点数与紫微解读</h2>
    {authenticated ? <div className="mt-3 flex gap-4">
      <span>已登录</span>
      <button disabled={busy} onClick={() => run(async () => { await accountRequest("/logout", {}); reload(); })}>退出此浏览器</button>
      <button disabled={busy} onClick={() => run(async () => { await accountRequest("/logout-all", {}); reload(); })}>退出所有浏览器</button>
    </div> : <form className="mt-3 flex flex-col gap-3" onSubmit={event => { event.preventDefault(); void run(async () => {
      if (challenge) { await accountRequest("/verify", { challenge_id: challenge, code }); reload(); }
      else { const result = await accountRequest<{ challenge_id: string }>("/challenges", { email, purpose }); setChallenge(result.challenge_id); setMessage("请查看邮箱中的验证码。验证码 15 分钟内有效。"); }
    }); }}>
      <label>操作 <select disabled={busy || !!challenge} className="mt-1 w-full rounded-md border border-slate-300 bg-white px-2 py-2 text-ink focus-visible:outline-violet-600" value={purpose} onChange={e => setPurpose(e.target.value as "bind" | "recover")}>
        <option value="recover">找回已验证账号</option><option value="bind">为此浏览器的账号绑定邮箱</option>
      </select></label>
      <p>绑定前请确认本浏览器的点数与档案。找回会退出其他浏览器；不会合并本浏览器的其他账号。灵签记录暂不包含在邮箱找回中。</p>
      <label>邮箱 <input required type="email" autoComplete="email" maxLength={255} disabled={busy || !!challenge} className="mt-1 w-full rounded-md border border-slate-300 bg-white px-2 py-2 text-ink focus-visible:outline-violet-600" value={email} onChange={e => setEmail(e.target.value)} /></label>
      {challenge && <label>验证码 <input required autoComplete="one-time-code" maxLength={128} className="mt-1 w-full rounded-md border border-slate-300 bg-white px-2 py-2 text-ink focus-visible:outline-violet-600" value={code} onChange={e => setCode(e.target.value.trim())} /></label>}
      <div className="flex gap-4"><button disabled={busy} type="submit">{busy ? "处理中…" : challenge ? "验证并登录" : "发送验证码"}</button>
        {challenge && <button disabled={busy} type="button" onClick={() => { setChallenge(""); setCode(""); setMessage(""); }}>重新获取 / 更换邮箱</button>}</div>
    </form>}
    {authenticated === null && <button type="button" disabled={busy} className="mt-3 underline" onClick={() => run(async () => { await accountRequest("/logout", {}); reload(); })}>清除本浏览器登录状态，重新选择找回方式</button>}
    {authenticated === false && <details className="mt-4 border-t border-violet-100 pt-3">
      <summary className="cursor-pointer font-medium">使用旧设备找回码（尚未绑定邮箱）</summary>
      <form className="mt-3 flex flex-col gap-3" onSubmit={event => { event.preventDefault(); if (!legacyConsent) return; void run(async () => { await restoreLegacyDevice(legacyCode); reload(); }); }}>
        <p>在新浏览器输入以前保存的设备找回码，查看原有档案后再绑定邮箱。已经绑定邮箱的账号必须通过邮箱找回。</p>
        <label>旧设备找回码 <input required type="password" autoComplete="off" maxLength={64} className="mt-1 w-full rounded-md border border-slate-300 bg-white px-2 py-2 text-ink" value={legacyCode} onChange={event => setLegacyCode(event.target.value)} /></label>
        <label className="flex items-start gap-2"><input required type="checkbox" checked={legacyConsent} onChange={event => setLegacyConsent(event.target.checked)} />我知道这会切换本浏览器紫微与灵签共用的旧设备身份，不会合并数据。</label>
        <button type="submit" disabled={busy || !legacyConsent}>恢复旧设备身份</button>
      </form>
    </details>}
    {message && <p role="status" className="mt-3">{message}</p>}
  </section>;
}
