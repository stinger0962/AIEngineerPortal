"use client";

import { useState } from "react";
import { PERSONA_LABELS } from "@/lib/ziwei/constants";
import { ziweiApi } from "@/lib/ziwei/api";

type PersonaSwitchProps = {
  profileId: number;
  persona: string;
  onChanged: (next: string) => void;
};

export function PersonaSwitch({ profileId, persona, onChanged }: PersonaSwitchProps) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleClick = async (next: string) => {
    if (next === persona || busy) return;
    setBusy(true);
    setError(null);
    try {
      await ziweiApi.updateProfile(profileId, { persona: next });
      onChanged(next);
    } catch {
      setError("切换失败");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-1.5 flex-wrap">
        <span className="text-[10px] text-violet-400/60 shrink-0">解盘师风格</span>
        {Object.entries(PERSONA_LABELS).map(([key, label]) => {
          const active = key === persona;
          return (
            <button
              key={key}
              type="button"
              disabled={busy}
              onClick={() => void handleClick(key)}
              className={
                active
                  ? "rounded-full px-2.5 py-1 text-xs bg-violet-600 text-white disabled:opacity-60 transition-colors"
                  : "rounded-full px-2.5 py-1 text-xs border border-violet-500/30 text-violet-300/70 hover:text-violet-100 disabled:opacity-40 transition-colors"
              }
            >
              {label}
            </button>
          );
        })}
      </div>
      {error ? <p className="text-[10px] text-rose-400">{error}</p> : null}
    </div>
  );
}
