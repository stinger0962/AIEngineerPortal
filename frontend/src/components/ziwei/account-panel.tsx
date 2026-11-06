"use client";

import { useEffect, useState } from "react";
import { accountRequest } from "@/lib/ziwei/account";

export function AccountPanel() {
  const [email, setEmail] = useState("");
  const [purpose, setPurpose] = useState<"bind" | "recover">("recover");
  const [challenge, setChallenge] = useState("");
  const [code, setCode] = useState("");
  const [authenticated, setAuthenticated] = useState(false);
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
  return <section className="rounded-xl border border-violet-400/20 p-4 text-sm text-violet-100" aria-label="邮箱账号">
    <h2 className="font-semibold">邮箱账号 · 点数与紫微解读</h2>
    {authenticated ? <div className="mt-3 flex gap-4">
      <span>已登录</span>
      <button disabled={busy} onClick={() => run(async () => { await accountRequest("/logout", {}); reload(); })}>退出此浏览器</button>
      <button disabled={busy} onClick={() => run(async () => { await accountRequest("/logout-all", {}); reload(); })}>退出所有浏览器</button>
    </div> : <form className="mt-3 flex flex-col gap-3" onSubmit={event => { event.preventDefault(); void run(async () => {
      if (challenge) { await accountRequest("/verify", { challenge_id: challenge, code }); reload(); }
      else { const result = await accountRequest<{ challenge_id: string }>("/challenges", { email, purpose }); setChallenge(result.challenge_id); setMessage("请查看邮箱中的验证码。验证码 15 分钟内有效。"); }
    }); }}>
      <label>操作 <select disabled={busy || !!challenge} className="bg-slate-900" value={purpose} onChange={e => setPurpose(e.target.value as "bind" | "recover")}>
        <option value="recover">找回已验证账号</option><option value="bind">为此浏览器的账号绑定邮箱</option>
      </select></label>
      <p>绑定前请确认本浏览器的点数与档案。找回会退出其他浏览器；不会合并本浏览器的其他账号。灵签记录暂不包含在邮箱找回中。</p>
      <label>邮箱 <input required type="email" autoComplete="email" maxLength={255} disabled={busy || !!challenge} className="bg-slate-900" value={email} onChange={e => setEmail(e.target.value)} /></label>
      {challenge && <label>验证码 <input required autoComplete="one-time-code" maxLength={128} className="bg-slate-900" value={code} onChange={e => setCode(e.target.value.trim())} /></label>}
      <div className="flex gap-4"><button disabled={busy} type="submit">{busy ? "处理中…" : challenge ? "验证并登录" : "发送验证码"}</button>
        {challenge && <button disabled={busy} type="button" onClick={() => { setChallenge(""); setCode(""); setMessage(""); }}>重新获取 / 更换邮箱</button>}</div>
    </form>}
    {message && <p role="status" className="mt-3">{message}</p>}
  </section>;
}
