export type NodeKind = "reading" | "scene" | "drill" | "boss";
export type NodeStatus = "locked" | "unlocked" | "completed";

export type MapNode = {
  slug: string;
  kind: NodeKind;
  title: string;
  order_index: number;
  status: NodeStatus;
  stars: number;
};

export type MapRegion = {
  slug: string;
  title: string;
  theme: string;
  order_index: number;
  nodes: MapNode[];
};

export type ReadingContent = {
  letters: { jamo: string; sound: string; audio_key: string }[];
  blocks: { ko: string; romaji: string }[];
  words: { ko: string; en: string }[];
};

export type SceneLine = { speaker: string; ko: string; romaji: string; en: string; audio_key: string };
export type SceneTurn = {
  prompt_en: string;
  options: string[];
  accepted: { ko: string; intents: string[] }[];
};
export type SceneContent = {
  setting: string;
  character: string;
  lines: SceneLine[];
  your_turns: SceneTurn[];
  new_vocab: { ko: string; en: string; romaji: string }[];
};

// Drills are tap-only (no writing): match the meaning, or listen and pick.
export type DrillItem =
  | { type: "match"; ko: string; answer: string; choices: string[] }
  | { type: "listen"; audio_key: string; answer: string; choices: string[] };
export type DrillContent = { items: DrillItem[] };

export type BossContent = {
  goal_en: string;
  persona: string;
  level: string;
  allowed_vocab: string[];
  success_criteria: string;
  max_turns: number;
};

export type NodeDetail = {
  slug: string;
  kind: NodeKind;
  title: string;
  order_index: number;
  content_json: ReadingContent | SceneContent | DrillContent | BossContent;
};
