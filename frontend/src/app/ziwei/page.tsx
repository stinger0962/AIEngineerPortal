"use client";

import { useEffect, useMemo, useState } from "react";
import { Plus, Sparkles, Trash2 } from "lucide-react";
import { ChartGrid2D } from "@/components/ziwei/chart-grid-2d";
import { ProfileForm } from "@/components/ziwei/profile-form";
import { hasChart, ziweiApi, type ZiweiProfileOut } from "@/lib/ziwei/api";
import { RELATION_LABELS } from "@/lib/ziwei/constants";

export default function ZiweiPage() {
  const [profiles, setProfiles] = useState<ZiweiProfileOut[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [loadError, setLoadError] = useState(false);

  useEffect(() => {
    ziweiApi
      .listProfiles()
      .then((data) => {
        setProfiles(data);
        if (data.length > 0) setSelectedId(data[0].id);
        else setShowForm(true);
      })
      .catch(() => setLoadError(true));
  }, []);

  const selected = useMemo(() => profiles.find((p) => p.id === selectedId) ?? null, [profiles, selectedId]);
  const chart = selected && hasChart(selected) ? selected.chart_json : null;

  const handleCreated = (profile: ZiweiProfileOut) => {
    setProfiles((prev) => [...prev, profile]);
    setSelectedId(profile.id);
    setShowForm(false);
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm("删除档案将一并删除其全部解读记录，确定？")) return;
    await ziweiApi.deleteProfile(id);
    setProfiles((prev) => {
      const next = prev.filter((p) => p.id !== id);
      if (selectedId === id) setSelectedId(next[0]?.id ?? null);
      return next;
    });
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

      <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
        {/* 档案列表 */}
        <div className="space-y-3">
          {profiles.map((profile) => (
            <button
              key={profile.id}
              onClick={() => setSelectedId(profile.id)}
              className={`group flex w-full items-center justify-between rounded-2xl border px-4 py-3 text-left transition-colors ${
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
              <Trash2
                size={16}
                className="text-ink/20 opacity-0 transition-opacity hover:text-rose-500 group-hover:opacity-100"
                onClick={(e) => {
                  e.stopPropagation();
                  void handleDelete(profile.id);
                }}
              />
            </button>
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
        </div>

        {/* 命盘 */}
        <div>
          {chart ? (
            <ChartGrid2D chart={chart} />
          ) : (
            <div className="flex min-h-[400px] items-center justify-center rounded-[28px] border border-ink/10 bg-[#0a0618]">
              <p className="text-sm text-violet-300/50">{profiles.length === 0 ? "建立第一个档案，开启星盘" : "档案缺少命盘数据"}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
