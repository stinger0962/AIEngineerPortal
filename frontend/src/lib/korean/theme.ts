import type { NodeKind } from "./types";

/** Per-node-type visual identity. `seal` is a single 한글/한자 stamp; `accent`/`soft`
 * are the obangsaek accent + its tinted surface. One source of truth for all node UI. */
export type KindTheme = {
  label: string;
  seal: string;
  accent: string;
  soft: string;
};

export const KIND_THEME: Record<NodeKind, KindTheme> = {
  reading: { label: "읽기 · Reading", seal: "한", accent: "var(--kr-reading)", soft: "#eaf3ef" },
  scene: { label: "장면 · Scene", seal: "말", accent: "var(--kr-scene)", soft: "#f7e9e1" },
  drill: { label: "연습 · Drill", seal: "연", accent: "var(--kr-drill)", soft: "#f5edda" },
  boss: { label: "도전 · Boss", seal: "왕", accent: "var(--kr-boss)", soft: "#e9eaf3" },
};

/** A small Korean seal for each region, keyed by its `theme` string (falls back to ✦). */
export const REGION_SEAL: Record<string, string> = {
  reading: "한",
  arrival: "착",
  cafe: "차",
  transit: "역",
  shopping: "돈",
};
