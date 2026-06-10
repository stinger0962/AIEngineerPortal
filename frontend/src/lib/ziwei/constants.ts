/** 时辰序号 0-12 对应的标签（与 iztro timeIndex 语义一致） */
export const TIME_LABELS = [
  "早子时 00:00-01:00",
  "丑时 01:00-03:00",
  "寅时 03:00-05:00",
  "卯时 05:00-07:00",
  "辰时 07:00-09:00",
  "巳时 09:00-11:00",
  "午时 11:00-13:00",
  "未时 13:00-15:00",
  "申时 15:00-17:00",
  "酉时 17:00-19:00",
  "戌时 19:00-21:00",
  "亥时 21:00-23:00",
  "晚子时 23:00-00:00",
] as const;

export const RELATION_LABELS: Record<string, string> = {
  self: "自己",
  family: "家人",
  friend: "朋友",
};

export const PERSONA_LABELS: Record<string, string> = {
  sage: "温和智者",
  taoist: "仙风道骨",
  analyst: "现代分析师",
};

/** 四化徽标配色 */
export const MUTAGEN_STYLES: Record<string, string> = {
  禄: "bg-emerald-500/90 text-white",
  权: "bg-amber-500/90 text-white",
  科: "bg-sky-500/90 text-white",
  忌: "bg-rose-500/90 text-white",
};
