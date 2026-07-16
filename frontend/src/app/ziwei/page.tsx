"use client";

import { useEffect, useMemo, useState } from "react";
import { Plus, Sparkles, Trash2 } from "lucide-react";
import { ProfileForm } from "@/components/ziwei/profile-form";
import { ZiweiWorkspace } from "@/components/ziwei/ziwei-workspace";
import { OracleIdentityPanel } from "@/components/oracle/identity-panel";
import { hasChart, ziweiApi, type ZiweiProfileOut } from "@/lib/ziwei/api";
import { RELATION_LABELS } from "@/lib/ziwei/constants";

export default function ZiweiPage() {
  const [profiles, setProfiles] = useState<ZiweiProfileOut[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [loadError, setLoadError] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    ziweiApi
      .listProfiles()
      .then((data) => {
        setProfiles(data);
        if (data.length > 0) setSelectedId(data[0].id);
        else setShowForm(true);
      })
      .catch(() => setLoadError(true))
      .finally(() => setLoading(false));
  }, []);

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

      {loadError ? <p className="text-sm text-rose-500">加载档案失败，请确认后端已启动。</p> : null}
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

          {showForm ? (
            <ProfileForm onCreated={handleCreated} onCancel={() => setShowForm(false)} />
          ) : (
            <button
              onClick={() => setShowForm(true)}
              className="flex w-full items-center justify-center gap-2 rounded-2xl border border-dashed border-violet-400/40 py-3 text-sm text-violet-600 transition-colors hover:bg-violet-600/5"
            >
              <Plus size={16} /> 新建命主档案
            </button>
          )}

          <OracleIdentityPanel />
        </div>

        {/* 命盘 */}
        <div>
          {selected && hasChart(selected) ? (
            <ZiweiWorkspace
              profile={selected}
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
