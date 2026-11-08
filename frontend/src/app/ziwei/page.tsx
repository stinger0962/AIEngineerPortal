"use client";

import { paidProduct } from "@/lib/product/config";
import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Plus, Sparkles, Trash2 } from "lucide-react";
import { ProfileForm } from "@/components/ziwei/profile-form";
import { ZiweiWorkspace } from "@/components/ziwei/ziwei-workspace";
import { OracleIdentityPanel } from "@/components/oracle/identity-panel";
import { hasChart, ziweiApi, type ZiweiProfileOut } from "@/lib/ziwei/api";
import { CreditPanel } from "@/components/ziwei/billing/credit-panel";
import { testBillingEnabled } from "@/lib/ziwei/billing";
import { RELATION_LABELS } from "@/lib/ziwei/constants";

export default function ZiweiPage() {
  const [balanceVersion, setBalanceVersion] = useState(0);
  const [profiles, setProfiles] = useState<ZiweiProfileOut[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [loadError, setLoadError] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const loadController = useRef<AbortController | null>(null);
  const loadVersion = useRef(0);
  const mounted = useRef(false);
  const loadProfiles = useCallback(async () => {
    const version = ++loadVersion.current;
    loadController.current?.abort();
    const controller = new AbortController(); loadController.current = controller;
    setLoading(true); setLoadError(false);
    const current = () => mounted.current && loadVersion.current === version && !controller.signal.aborted;
    try {
      const data = await ziweiApi.listProfiles(controller.signal);
      if (!Array.isArray(data) || data.some(profile => !profile || !Number.isSafeInteger(profile.id) || profile.id < 1
        || typeof profile.name !== "string" || typeof profile.relation !== "string" || typeof profile.gender !== "string"
        || typeof profile.birth_date !== "string" || typeof profile.persona !== "string"
        || !profile.chart_json || typeof profile.chart_json !== "object" || Array.isArray(profile.chart_json)
        || ("palaces" in profile.chart_json && !Array.isArray(profile.chart_json.palaces)))) {
        throw new Error("Invalid profile list");
      }
      if (!current()) return;
      setProfiles(data);
      if (data.length > 0) {
        let restored: number | null = null;
        if (testBillingEnabled) {
          try { restored = Number(sessionStorage.getItem("ziwei-selected-profile")); } catch { /* storage unavailable */ }
        }
        setSelectedId(previous => data.find(profile => profile.id === previous)?.id
          ?? data.find(profile => profile.id === restored)?.id ?? data[0].id);
        setShowForm(false);
      } else { setSelectedId(null); setShowForm(true); }
    } catch {
      if (current()) setLoadError(true);
    } finally {
      if (current()) setLoading(false);
    }
  }, []);
  useEffect(() => {
    mounted.current = true;
    void loadProfiles();
    return () => { mounted.current = false; ++loadVersion.current; loadController.current?.abort(); };
  }, [loadProfiles]);

  useEffect(() => {
    if (!testBillingEnabled || selectedId === null) return;
    try { sessionStorage.setItem("ziwei-selected-profile", String(selectedId)); } catch { /* storage unavailable */ }
  }, [selectedId]);

  const selected = useMemo(() => profiles.find((p) => p.id === selectedId) ?? null, [profiles, selectedId]);

  const handleCreated = (profile: ZiweiProfileOut) => {
    setProfiles((prev) => [...prev, profile]);
    setSelectedId(profile.id);
    setShowForm(false);
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm("删除档案将一并删除其全部解读记录，确定？")) return;
    setDeleteError(null);
    try {
      await ziweiApi.deleteProfile(id);
    } catch {
      setDeleteError("删除失败，请稍后重试");
      return;
    }
    const next = profiles.filter((p) => p.id !== id);
    setProfiles(next);
    if (selectedId === id) setSelectedId(next[0]?.id ?? null);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-[14px] bg-gradient-to-br from-violet-600 via-violet-700 to-[#2d1a6e] text-white shadow-[0_6px_16px_-6px_rgba(124,58,237,0.6)]">
          <Sparkles className="h-6 w-6" strokeWidth={2} />
        </div>
        <div>
          <span className="text-xs font-semibold uppercase tracking-[0.28em] text-violet-600">星垣 · Astrolabe</span>
          <h1 className="font-display text-2xl leading-tight text-ink">紫微斗数</h1>
        </div>
      </div>

      {testBillingEnabled && <Suspense fallback={null}><CreditPanel refreshKey={balanceVersion} /></Suspense>}

      {loadError && <div className="space-y-2">
        <p className="text-sm text-rose-500" role="alert">暂时无法读取档案，请重试。已有档案不会因此丢失。</p>
        <button type="button" className="rounded-lg border border-violet-300 px-4 py-2 text-sm text-violet-800" onClick={() => void loadProfiles()}>重试读取档案</button>
      </div>}
      {loading && <p role="status" className="text-sm text-ink/70">正在读取档案…</p>}
      {deleteError ? (
        <p className="text-sm text-rose-500" role="alert">
          {deleteError}
        </p>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
        {/* 档案列表 */}
        <div className="space-y-3">
          {profiles.map((profile) => (
            <div key={profile.id} className="group relative">
              <button
                onClick={() => setSelectedId(profile.id)}
                className={`flex w-full items-center justify-between rounded-2xl border px-4 py-3 text-left transition-colors ${
                  profile.id === selectedId
                    ? "border-violet-500/60 bg-violet-600/10"
                    : "border-ink/10 bg-white/85 hover:border-violet-400/40"
                }`}
              >
                <div>
                  <p className="text-sm font-semibold text-ink">{profile.name}</p>
                  <p className="text-xs text-ink/50">
                    {RELATION_LABELS[profile.relation] ?? profile.relation} · {profile.gender === "female" ? "女" : "男"} ·{" "}
                    {profile.birth_date}
                  </p>
                </div>
              </button>
              <button
                type="button"
                aria-label={`删除 ${profile.name}`}
                onClick={() => void handleDelete(profile.id)}
                className={`absolute right-3 top-1/2 -translate-y-1/2 rounded p-1 transition-opacity hover:text-rose-500 focus-visible:opacity-100 group-hover:opacity-100 ${
                  profile.id === selectedId ? "text-ink/40 opacity-100" : "text-ink/20 opacity-0"
                }`}
              >
                <Trash2 size={16} />
              </button>
            </div>
          ))}

          {!loading && !loadError && (showForm ? (
            <ProfileForm onCreated={handleCreated} onCancel={() => setShowForm(false)} />
          ) : (
            <button
              onClick={() => setShowForm(true)}
              className="flex w-full items-center justify-center gap-2 rounded-2xl border border-dashed border-violet-400/40 py-3 text-sm text-violet-600 transition-colors hover:bg-violet-600/5"
            >
              <Plus size={16} /> 新建命主档案
            </button>
          ))}

          {!paidProduct && <OracleIdentityPanel />}
        </div>

        {/* 命盘 */}
        <div>
          {selected && hasChart(selected) ? (
            <ZiweiWorkspace
              profile={selected}
              onReadingSuccess={() => setBalanceVersion((value) => value + 1)}
              onPersonaChange={(next) =>
                setProfiles((prev) =>
                  prev.map((p) => (p.id === selected.id ? { ...p, persona: next } : p)),
                )
              }
            />
          ) : (
            <div className="flex min-h-[400px] items-center justify-center rounded-[28px] border border-ink/10 bg-[#0a0618]">
              <p className="text-sm text-violet-300/50">
                {loadError ? "档案加载失败" : loading ? "载入中……" : profiles.length === 0 ? "建立第一个档案，开启星盘" : "档案缺少命盘数据"}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
