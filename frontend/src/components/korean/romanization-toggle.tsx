"use client";
import { useEffect, useState } from "react";

const KEY = "korean.romaji";

export function useRomaji(): [boolean, (v: boolean) => void] {
  const [on, setOn] = useState(true);
  useEffect(() => {
    const saved = localStorage.getItem(KEY);
    if (saved !== null) setOn(saved === "1");
  }, []);
  const set = (v: boolean) => {
    setOn(v);
    localStorage.setItem(KEY, v ? "1" : "0");
  };
  return [on, set];
}

export function RomanizationToggle({ on, onChange }: { on: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex items-center gap-2 text-xs opacity-70">
      <input type="checkbox" checked={on} onChange={(e) => onChange(e.target.checked)} />
      Show romanization
    </label>
  );
}
