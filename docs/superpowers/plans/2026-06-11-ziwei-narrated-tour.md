# 紫微解盘 · 叙事化播放 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把紫微解盘的播放从「尽快打字」改成「以声音为主时钟的叙事化导览」——镜头慢飞停驻、声音解说、结束揭全文脚本。

**Architecture:** 复用流式端点喂一个「节拍队列」；指挥器（`useOracleTour`）逐拍表演（镜头先慢飞→再朗读这段），声音源是可替换接口（V1 浏览器语音，默认出声；V2 云 TTS）。纯前端，后端零改动。

**Tech Stack:** Next.js 15 / React 19 / TypeScript、Web Speech API（`speechSynthesis`）、现有 `streamOracle`（SSE）、`@react-three/drei` 的 `CameraControls`（`smoothTime` 控过渡时长）。

**测试约定（重要）：** 本仓库前端**没有单元测试框架**（无 vitest/jest；前三期都靠 `tsc --noEmit` + CI `next build` + 浏览器/prod 肉眼确认）。本计划遵循既有模式：每个任务的「验证」= `npx tsc --noEmit` 对所改文件**不引入新错误**（注意：`scene3d/*` 与 `camera-rig.tsx` 因本地未装 `three/drei` 会有**既存**的 module-resolution 报错，只看有没有**新增**错误）+ 关键纯逻辑用一次性 `node` 脚本跑通后删除 + 最终 CI `next build` 是真正门槛 + prod 浏览器确认体验。不新增测试框架（遵循「在既有代码库里跟随既有模式」）。

**全局常量（贯穿各任务，定义在 `use-oracle-tour.ts` 顶部）：**
```ts
const SETTLE_MS = 550;      // 镜头起步到开口的留白
const GAP_MS = 300;         // 拍间小停
const EMPTY_DWELL_MS = 900; // 纯镜头空拍的停驻
const TOUR_SMOOTH = 1.5;    // 解读期镜头过渡秒数
const IDLE_SMOOTH = 0.45;   // 平时（手动拖拽）镜头过渡秒数
```

---

## Task 1: 可替换声音源 `narration.ts`

**Files:**
- Create: `frontend/src/lib/ziwei/narration.ts`

声音源接口 + 浏览器实现 + 静音实现 + 时长估算。无任何 3D / alias 依赖，`tsc` 可完整校验。

- [ ] **Step 1: 写 `narration.ts`**

```ts
// frontend/src/lib/ziwei/narration.ts
"use client";

/** 一段解说的播放源：speak 在朗读结束（或定时结束）时 resolve；cancel 立即停止。
 * V1 用浏览器 SpeechSynthesis；V2 只需新增 CloudNarration，指挥器与 UI 不变。 */
export interface NarrationSource {
  speak(text: string): Promise<void>;
  cancel(): void;
}

/** 估算朗读时长（静音/无语音时给指挥器一个节拍时钟）。 */
export function estimateDuration(text: string): number {
  const ms = text.length * 180;
  return Math.min(Math.max(ms, 800), 12000);
}

/** 浏览器内置语音（默认方案）。挑 zh-CN 嗓音，语速略慢契合解盘调性。 */
export class BrowserNarration implements NarrationSource {
  private current: SpeechSynthesisUtterance | null = null;

  static isSupported(): boolean {
    return typeof window !== "undefined" && "speechSynthesis" in window;
  }

  private pickVoice(): SpeechSynthesisVoice | null {
    const voices = window.speechSynthesis.getVoices();
    return (
      voices.find((v) => v.lang === "zh-CN") ??
      voices.find((v) => v.lang?.toLowerCase().startsWith("zh")) ??
      null
    );
  }

  speak(text: string): Promise<void> {
    if (!BrowserNarration.isSupported() || !text.trim()) return Promise.resolve();
    return new Promise<void>((resolve) => {
      const u = new SpeechSynthesisUtterance(text);
      u.lang = "zh-CN";
      u.rate = 0.92;
      const voice = this.pickVoice();
      if (voice) u.voice = voice;
      // onend 与 onerror 都 resolve：朗读失败时降级为静默继续，绝不卡死指挥器
      u.onend = () => { this.current = null; resolve(); };
      u.onerror = () => { this.current = null; resolve(); };
      this.current = u;
      window.speechSynthesis.speak(u);
    });
  }

  cancel(): void {
    this.current = null;
    if (BrowserNarration.isSupported()) window.speechSynthesis.cancel();
  }
}

/** 静音/不支持时用：按估算时长定时，让画面编排照常有节拍。 */
export class SilentNarration implements NarrationSource {
  private timer: ReturnType<typeof setTimeout> | null = null;
  private resolveFn: (() => void) | null = null;

  speak(text: string): Promise<void> {
    if (!text.trim()) return Promise.resolve();
    return new Promise<void>((resolve) => {
      this.resolveFn = resolve;
      this.timer = setTimeout(() => {
        this.timer = null;
        this.resolveFn = null;
        resolve();
      }, estimateDuration(text));
    });
  }

  cancel(): void {
    if (this.timer) clearTimeout(this.timer);
    this.timer = null;
    const r = this.resolveFn;
    this.resolveFn = null;
    r?.();
  }
}
```

- [ ] **Step 2: 验证 `estimateDuration` 逻辑（一次性脚本，跑完即删）**

写临时文件 `frontend/scratch-dur.mjs`：
```js
const estimateDuration = (text) => Math.min(Math.max(text.length * 180, 800), 12000);
console.log(estimateDuration(""), "==800?", estimateDuration("") === 800);
console.log(estimateDuration("十个字十个字十个字"), "==", 9 * 180 > 800 ? 9 * 180 : 800);
console.log(estimateDuration("x".repeat(1000)), "==12000?", estimateDuration("x".repeat(1000)) === 12000);
```
Run: `node frontend/scratch-dur.mjs`
Expected: `800 ==800? true` / `1620 == 1620` / `12000 ==12000? true`
然后删除：`rm frontend/scratch-dur.mjs`

- [ ] **Step 3: 类型检查**

Run: `cd frontend && npx tsc --noEmit`
Expected: 不出现任何指向 `lib/ziwei/narration.ts` 的错误（该文件无 3D/alias 依赖，应完全干净）。

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/ziwei/narration.ts
git commit -m "feat(ziwei): swappable NarrationSource (browser speech + silent + estimateDuration)"
```

---

## Task 2: 指挥器 `use-oracle-tour.ts`（节拍队列 + 逐拍表演 + skip/cancel/mute）

**Files:**
- Create: `frontend/src/components/ziwei/chat-dock/use-oracle-tour.ts`

这是本期的核心。包含：`BeatQueue`（异步队列）、把流式事件分拍的 handlers、逐拍表演循环（镜头先飞→再朗读）、skip/cancel/mute、以及历史「重新解读」用的合成流。

- [ ] **Step 1: 写 `use-oracle-tour.ts`**

```ts
// frontend/src/components/ziwei/chat-dock/use-oracle-tour.ts
"use client";

import { useRef, useCallback } from "react";
import type { CameraCommand, OracleSegment, OracleStreamHandlers } from "@/lib/ziwei/api";
import type { ZiweiChart } from "@/lib/ziwei/types";
import type { TermInfo } from "../term-card";
import { fireCamera } from "./camera";
import { BrowserNarration, SilentNarration, type NarrationSource } from "@/lib/ziwei/narration";

const SETTLE_MS = 550;
const GAP_MS = 300;
const EMPTY_DWELL_MS = 900;

const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

/** 一拍 =（前导文字 + 紧随的镜头指令）。command 为 null 表示收尾无镜头段。 */
type Beat = { text: string; command: CameraCommand | null };

/** 单生产者/单消费者异步队列：流处理器 push，表演循环 next。 */
class BeatQueue {
  private items: Beat[] = [];
  private closed = false;
  private waiter: (() => void) | null = null;
  convId: number | null = null;
  errored = false;

  push(b: Beat): void {
    this.items.push(b);
    this.wake();
  }
  close(convId: number | null, errored = false): void {
    this.convId = convId;
    this.errored = errored;
    this.closed = true;
    this.wake();
  }
  private wake(): void {
    const w = this.waiter;
    this.waiter = null;
    w?.();
  }
  /** 取下一拍；队空且已关闭 → null。 */
  async next(): Promise<Beat | null> {
    while (true) {
      if (this.items.length) return this.items.shift()!;
      if (this.closed) return null;
      await new Promise<void>((res) => { this.waiter = res; });
    }
  }
}

function captionFor(cmd: CameraCommand | null): string {
  if (!cmd) return "";
  if (cmd.type === "focus_palace") return ` · ${cmd.palace}`;
  if (cmd.type === "overview") return " · 通盘";
  if (cmd.type === "explain_term") return ` · ${cmd.term}`;
  return "";
}

export type TourDeps = {
  chart: ZiweiChart;
  onFocusBranch: (b: string | null) => void;
  onTerm: (t: TermInfo | null) => void;
  onCaption: (c: string | null) => void;     // 极简提示（当前宫名）
  onReveal: (full: string) => void;          // 把已得全文写进助手气泡
  onTourActiveChange: (active: boolean) => void; // 上抛给 workspace 控镜头速度
  reducedMotion: boolean;
};

export function useOracleTour() {
  const queueRef = useRef<BeatQueue | null>(null);
  const browserRef = useRef<NarrationSource | null>(null);
  const silentRef = useRef<NarrationSource>(new SilentNarration());
  const mutedRef = useRef(false);
  const skippedRef = useRef(false);
  const cancelledRef = useRef(false);

  const getNarration = (): NarrationSource => {
    if (mutedRef.current || cancelledRef.current) return silentRef.current;
    if (!browserRef.current) browserRef.current = new BrowserNarration();
    return browserRef.current;
  };

  /** 重置一次新解读的内部状态，返回喂给 streamOracle 的 handlers。 */
  const begin = useCallback((): { queue: BeatQueue; handlers: OracleStreamHandlers } => {
    const queue = new BeatQueue();
    queueRef.current = queue;
    skippedRef.current = false;
    cancelledRef.current = false;
    let buf = "";
    const handlers: OracleStreamHandlers = {
      onText: (delta) => { buf += delta; },
      onCamera: (command) => { queue.push({ text: buf, command }); buf = ""; },
      onDone: (cid) => {
        if (buf.trim()) queue.push({ text: buf, command: null });
        buf = "";
        queue.close(cid, false);
      },
      onError: () => {
        if (buf.trim()) queue.push({ text: buf, command: null });
        buf = "";
        queue.close(null, true);
      },
    };
    return { queue, handlers };
  }, []);

  /** 消费队列、逐拍表演。返回 Promise，外层 await 它得知表演结束。 */
  const play = useCallback(async (queue: BeatQueue, deps: TourDeps): Promise<void> => {
    deps.onTourActiveChange(true);
    let full = "";
    try {
      while (true) {
        const beat = await queue.next();
        if (beat === null) break;
        full += beat.text;

        if (cancelledRef.current) continue;        // 取消：排空但不表演不揭晓
        if (skippedRef.current || deps.reducedMotion) {
          deps.onReveal(full.trim());              // 跳过/降级：直出已得全文
          continue;
        }
        // 正常表演：镜头先动 → 留白 → 朗读这段 → 拍间小停
        deps.onCaption(captionFor(beat.command));
        if (beat.command) fireCamera(beat.command, { chart: deps.chart, onFocusBranch: deps.onFocusBranch, onTerm: deps.onTerm });
        await sleep(SETTLE_MS);
        if (cancelledRef.current) continue;
        if (beat.text.trim()) await getNarration().speak(beat.text.trim());
        else await sleep(EMPTY_DWELL_MS);
        await sleep(GAP_MS);
      }
    } finally {
      deps.onCaption(null);
      deps.onTourActiveChange(false);
    }
    if (cancelledRef.current) return;              // 取消不揭晓（外层会重置消息区）
    deps.onReveal(full.trim());                    // 收尾揭全文
    deps.onTerm(null);
    deps.onFocusBranch(null);                       // 缓回总览
    queue.convId !== null && void 0;                // convId 由外层从 onDone 拿，这里不强用
  }, []);

  /** 跳过：停声音+镜头，转「直出」——后续拍只累积+揭晓，不再表演。 */
  const skip = useCallback(() => {
    skippedRef.current = true;
    browserRef.current?.cancel();
    silentRef.current.cancel();
  }, []);

  /** 取消：彻底放弃本次表演（切档案/重新提问）。关队列让 play 退出。 */
  const cancel = useCallback(() => {
    cancelledRef.current = true;
    browserRef.current?.cancel();
    silentRef.current.cancel();
    queueRef.current?.close(null, false);
  }, []);

  /** 静音切换：静音时立刻掐断当前朗读，后续拍走 SilentNarration。 */
  const setMuted = useCallback((muted: boolean) => {
    mutedRef.current = muted;
    if (muted) browserRef.current?.cancel();
  }, []);

  /** 历史「重新解读」：把已存 segments 合成成一个立即就绪的队列（不调 AI）。 */
  const beginFromSegments = useCallback((segments: OracleSegment[]): BeatQueue => {
    const queue = new BeatQueue();
    queueRef.current = queue;
    skippedRef.current = false;
    cancelledRef.current = false;
    for (const seg of segments) {
      const cmd = seg.commands[0] ?? null;
      queue.push({ text: seg.text ?? "", command: cmd });
    }
    queue.close(null, false);
    return queue;
  }, []);

  return { begin, play, skip, cancel, setMuted, beginFromSegments };
}
```

- [ ] **Step 2: 验证「分拍」与「队列」逻辑（一次性脚本，跑完即删）**

写临时文件 `frontend/scratch-beats.mjs`（用纯 JS 镜像 BeatQueue + handlers 分拍，验证拍序与镜头先于朗读的不变量）：
```js
class BeatQueue {
  constructor() { this.items = []; this.closed = false; this.waiter = null; this.convId = null; }
  push(b) { this.items.push(b); const w = this.waiter; this.waiter = null; w && w(); }
  close(c) { this.convId = c; this.closed = true; const w = this.waiter; this.waiter = null; w && w(); }
  async next() {
    while (true) {
      if (this.items.length) return this.items.shift();
      if (this.closed) return null;
      await new Promise((res) => { this.waiter = res; });
    }
  }
}
// 模拟流：文字…[focus 命宫]…文字…[term]…收尾文字 + done
const q = new BeatQueue();
let buf = "";
const onText = (d) => { buf += d; };
const onCamera = (c) => { q.push({ text: buf, command: c }); buf = ""; };
const onDone = (cid) => { if (buf.trim()) q.push({ text: buf, command: null }); buf = ""; q.close(cid); };

onText("你命宫紫微。");
onCamera({ type: "focus_palace", palace: "命宫" });
onText("这是机月同梁格。");
onCamera({ type: "explain_term", term: "机月同梁格", explanation: "稳健之格" });
onText("总体宜稳。");
onDone(42);

(async () => {
  const beats = [];
  let b;
  while ((b = await q.next()) !== null) beats.push(b);
  console.log(JSON.stringify(beats, null, 0));
  console.log("拍数==3?", beats.length === 3);
  console.log("拍1镜头是命宫?", beats[0].command.palace === "命宫" && beats[0].text.includes("命宫紫微"));
  console.log("末拍无镜头?", beats[2].command === null && beats[2].text.includes("宜稳"));
  console.log("convId==42?", q.convId === 42);
})();
```
Run: `node frontend/scratch-beats.mjs`
Expected: `拍数==3? true` / `拍1镜头是命宫? true` / `末拍无镜头? true` / `convId==42? true`
然后删除：`rm frontend/scratch-beats.mjs`

- [ ] **Step 3: 类型检查**

Run: `cd frontend && npx tsc --noEmit`
Expected: 不出现指向 `chat-dock/use-oracle-tour.ts` 的错误（它只 import 现有类型 + narration + camera，无 3D 依赖，应干净）。

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/ziwei/chat-dock/use-oracle-tour.ts
git commit -m "feat(ziwei): oracle tour conductor (beat queue + camera-first-then-narrate + skip/cancel/mute)"
```

---

## Task 3: 慢镜头——`CameraRig` 加 `smoothTime` prop 并穿线 `tourActive`

**Files:**
- Modify: `frontend/src/components/ziwei/scene3d/camera-rig.tsx`
- Modify: `frontend/src/components/ziwei/scene3d/scene-3d.tsx`
- Modify: `frontend/src/components/ziwei/chart-view.tsx`
- Modify: `frontend/src/components/ziwei/ziwei-workspace.tsx`

`tourActive` 从 workspace 一路下传到 CameraRig，解读期把 `smoothTime` 由 0.45 提到 1.5。

- [ ] **Step 1: `camera-rig.tsx` 加 `smoothTime` prop**

把签名与 `CameraControls` 改成：
```tsx
export function CameraRig({ selectedBranch, smoothTime = 0.45 }: { selectedBranch: string | null; smoothTime?: number }) {
```
并把 effect 依赖加上 `smoothTime`（切速度时无需重新运镜，但保持一致无害可不加），`CameraControls` 的 prop 改为：
```tsx
      smoothTime={smoothTime}
```
（其余不动。）

- [ ] **Step 2: `scene-3d.tsx` 透传**

`Scene3DProps` 加 `tourActive?: boolean`：
```tsx
export type Scene3DProps = {
  chart: ZiweiChart;
  selectedBranch: string | null;
  onSelectBranch: (branch: string | null) => void;
  onRenderError?: () => void;
  tourActive?: boolean;
};
```
解构加 `tourActive`，并把 CameraRig 那行改为：
```tsx
        <CameraRig selectedBranch={selectedBranch} smoothTime={tourActive ? 1.5 : 0.45} />
```

- [ ] **Step 3: `chart-view.tsx` 透传**

`ChartView` props 加 `tourActive?: boolean`：
```tsx
export function ChartView({
  chart,
  selectedBranch,
  onSelectBranch,
  tourActive,
}: {
  chart: ZiweiChart;
  selectedBranch: string | null;
  onSelectBranch: (b: string | null) => void;
  tourActive?: boolean;
}) {
```
并把 `<Scene3D ... />` 加上 `tourActive={tourActive}`：
```tsx
          <Scene3D
            chart={chart}
            selectedBranch={selectedBranch}
            onSelectBranch={onSelectBranch}
            onRenderError={() => setRenderFailed(true)}
            tourActive={tourActive}
          />
```

- [ ] **Step 4: `ziwei-workspace.tsx` 持有 `tourActive`**

加状态 + 切档案重置 + 下传：
```tsx
  const [selectedBranch, setSelectedBranch] = useState<string | null>(null);
  const [term, setTerm] = useState<TermInfo | null>(null);
  const [tourActive, setTourActive] = useState(false);

  const [prevId, setPrevId] = useState(profile.id);
  if (prevId !== profile.id) {
    setPrevId(profile.id);
    setSelectedBranch(null);
    setTerm(null);
    setTourActive(false);
  }
```
`<ChartView ... />` 加 `tourActive={tourActive}`；`<ChatDock ... />` 加 `onTourActiveChange={setTourActive}`：
```tsx
      <ChartView chart={chart} selectedBranch={selectedBranch} onSelectBranch={setSelectedBranch} tourActive={tourActive} />
      {term ? <TermCard info={term} onClose={() => setTerm(null)} /> : null}
      <ChatDock
        profileId={profile.id}
        persona={profile.persona}
        chart={chart}
        onFocusBranch={setSelectedBranch}
        onTerm={setTerm}
        onPersonaChange={onPersonaChange ?? (() => {})}
        onTourActiveChange={setTourActive}
      />
```

- [ ] **Step 5: 类型检查（看新增错误，不看既存 3D module 噪声）**

Run: `cd frontend && npx tsc --noEmit`
Expected: `camera-rig.tsx`/`scene-3d.tsx` 仍有**既存**的 `Cannot find module 'three'/'@react-three/drei'/'camera-controls'` 报错（本地未装依赖，CI 会装），但**不得**出现新的「prop 不存在/类型不匹配」错误，且 `chart-view.tsx`/`ziwei-workspace.tsx`（不直接 import three）应干净。CI `next build` 是真正门槛。

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/ziwei/scene3d/camera-rig.tsx frontend/src/components/ziwei/scene3d/scene-3d.tsx frontend/src/components/ziwei/chart-view.tsx frontend/src/components/ziwei/ziwei-workspace.tsx
git commit -m "feat(ziwei): thread tourActive to slow camera (smoothTime 0.45->1.5) during reading"
```

---

## Task 4: chat-dock 改走指挥器 + 解读态 UI（提示行 + 🔇 + 跳过 + 首次出声提示）

**Files:**
- Modify: `frontend/src/components/ziwei/chat-dock/chat-dock.tsx`
- Modify: `frontend/src/components/ziwei/chat-dock/types.ts`

`handleSend` 改成：起流 + 跑指挥器；解读期气泡只显极简提示行（含静音/跳过）；结束揭全文。新增 `onTourActiveChange` prop、`caption`/`muted` 状态、首次出声 localStorage 提示。

- [ ] **Step 1: `types.ts` 给 `ChatMessage` 加 `segments` 已有；无需改。确认即可。**

`ChatMessage` 已含 `segments?: OracleSegment[]`、`cameras?`、`pending?`，本任务复用 `pending` 表示「解读中」。无需修改 types.ts。（此步仅确认，不产生改动。）

- [ ] **Step 2: 改 `chat-dock.tsx` 顶部 import 与 props**

import 增加指挥器：
```tsx
import { useOracleTour } from "./use-oracle-tour";
```
（删掉对 `fireCamera`/`camera` 的直接 import——改由指挥器内部用；若 chat-dock 不再直接调用 fireCamera 则移除该 import。）

`ChatDockProps` 加 `onTourActiveChange`：
```tsx
type ChatDockProps = {
  profileId: number;
  persona: string;
  chart: ZiweiChart;
  onFocusBranch: (branch: string | null) => void;
  onTerm: (t: TermInfo | null) => void;
  onPersonaChange: (next: string) => void;
  onTourActiveChange: (active: boolean) => void;
};
```
解构加 `onTourActiveChange`。

- [ ] **Step 3: 组件内新增状态与指挥器实例**

在现有 `useState` 群附近加：
```tsx
  const tour = useOracleTour();
  const [caption, setCaption] = useState<string | null>(null);
  const [muted, setMuted] = useState(false);
  const [audioHintSeen, setAudioHintSeen] = useState(true); // 默认不显，挂载后读 localStorage 决定

  useEffect(() => {
    try {
      setAudioHintSeen(window.localStorage.getItem("ziwei-audio-hint") === "1");
    } catch {
      setAudioHintSeen(true);
    }
  }, []);

  const dismissAudioHint = () => {
    setAudioHintSeen(true);
    try { window.localStorage.setItem("ziwei-audio-hint", "1"); } catch { /* 隐私模式忽略 */ }
  };

  const toggleMuted = () => {
    setMuted((m) => {
      const next = !m;
      tour.setMuted(next);
      return next;
    });
  };
```
把原 `abortRef` 保留。原 `replay`/`fireCamera` 相关已无（流式版已删 replay），确认无残留引用。

- [ ] **Step 4: 切档案/载入历史时也取消指挥器**

`if (prevId !== profileId)` 块内、`handleLoadConversation` 内，在 `abortRef.current?.abort()` 之后各加一行 `tour.cancel();`，并 `setCaption(null)`：
```tsx
  if (prevId !== profileId) {
    setPrevId(profileId);
    abortRef.current?.abort();
    tour.cancel();
    setMessages([]);
    setConversationId(null);
    setError(null);
    setInput("");
    setShowHistory(false);
    setCaption(null);
  }
```
```tsx
  const handleLoadConversation = (loadedConversationId: number, mapped: ChatMessage[]) => {
    abortRef.current?.abort();
    tour.cancel();
    setMessages(mapped);
    setConversationId(loadedConversationId);
    setShowHistory(false);
    setCaption(null);
  };
```

- [ ] **Step 5: 重写 `handleSend` 走指挥器**

```tsx
  const handleSend = async () => {
    const message = input.trim();
    if (!message || loading) return;

    abortRef.current?.abort();
    tour.cancel();
    const controller = new AbortController();
    abortRef.current = controller;

    const userMsg: ChatMessage = { id: crypto.randomUUID(), role: "user", content: message };
    const assistantId = crypto.randomUUID();
    setMessages((prev) => [
      ...prev,
      userMsg,
      { id: assistantId, role: "assistant", content: "", pending: true },
    ]);
    setLoading(true);
    setError(null);
    setInput("");
    setCaption(null);

    const reqProfileId = profileId;
    const reduced =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const { queue, handlers } = tour.begin();
    tour.setMuted(muted);

    const setAssistant = (content: string, pending: boolean) =>
      setMessages((prev) => prev.map((m) => (m.id === assistantId ? { ...m, content, pending } : m)));

    // 指挥器消费循环（并发于 streamOracle）
    const playPromise = tour.play(queue, {
      chart,
      onFocusBranch,
      onTerm,
      onCaption: (c) => { if (reqProfileId === profileId) setCaption(c); },
      onReveal: (full) => { if (reqProfileId === profileId) { setLoading(false); setAssistant(full, false); } },
      onTourActiveChange,
      reducedMotion: reduced,
    });

    try {
      await ziweiApi.streamOracle(profileId, { scenario: "natal", message, conversation_id: conversationId ?? undefined }, handlers, controller.signal);
    } catch (e) {
      tour.cancel(); // 关队列让 play 退出（校验错误或 abort）
      if (e instanceof DOMException && e.name === "AbortError") { await playPromise; return; }
      setMessages((prev) => prev.filter((m) => !(m.id === assistantId && m.content === "")));
      if (e instanceof ZiweiApiError) {
        if (e.status === 503) setError("解盘师未启用（缺少 API Key）");
        else if (e.status === 429) setError("今日额度已用尽，请明日再来");
        else setError("解盘暂不可用，请稍后再试");
      } else {
        setError("解盘暂不可用，请稍后再试");
      }
      setLoading(false);
      setCaption(null);
      await playPromise;
      return;
    }

    await playPromise;
    // 落定会话 id（onDone 已把 convId 放进 queue）
    if (reqProfileId === profileId && queue.convId !== null) setConversationId(queue.convId);
    setLoading(false);
  };
```

注意：`onReveal` 里调用 `setLoading(false)` 让「凝神观盘」在第一拍揭晓时消失；正常流程第一拍开口前仍 loading。若希望 loading 在「首拍开口」就消失而非「揭晓」，可在 `onCaption` 首次非空时也 `setLoading(false)`——本版以揭晓为准，简洁优先。

- [ ] **Step 6: 解读态 UI——气泡内提示行 + 静音/跳过；首次出声提示**

把助手消息渲染块（`m.role === "assistant"` 分支）改成：pending 且无内容时显示提示行，否则显示正文。定位到现有 assistant 渲染：
```tsx
          ) : (
            <div key={m.id} className="whitespace-pre-wrap text-sm leading-relaxed text-violet-100">
              {m.pending && !m.content ? (
                <div className="flex items-center gap-2 text-violet-300/80">
                  <span className="animate-pulse">✦ 解盘师正在解读{caption ?? ""}</span>
                  <button type="button" onClick={toggleMuted} aria-label={muted ? "取消静音" : "静音"} className="rounded px-1.5 py-0.5 text-xs text-violet-300/70 hover:text-violet-100">
                    {muted ? "🔇" : "🔊"}
                  </button>
                  <button type="button" onClick={tour.skip} className="rounded px-1.5 py-0.5 text-xs text-violet-300/70 hover:text-violet-100">
                    直接看文字
                  </button>
                </div>
              ) : (
                <>
                  {m.content}
                  {m.pending ? <span className="animate-pulse text-violet-300/70">▌</span> : null}
                </>
              )}
            </div>
          ),
```
在消息区顶部（`messages.length === 0` 提示附近）加首次出声提示：
```tsx
        {!audioHintSeen ? (
          <div className="flex items-center justify-between gap-2 rounded-lg border border-violet-500/30 bg-violet-600/10 px-3 py-2 text-xs text-violet-200">
            <span>🔊 解读将有声朗读，可随时静音</span>
            <button type="button" onClick={dismissAudioHint} className="text-violet-300/70 hover:text-violet-100">知道了</button>
          </div>
        ) : null}
```

- [ ] **Step 7: 类型检查**

Run: `cd frontend && npx tsc --noEmit`
Expected: `chat-dock.tsx` 无新错误（它不 import 3D 库；只用现有 api/types/term-card/指挥器）。

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/ziwei/chat-dock/chat-dock.tsx
git commit -m "feat(ziwei): chat dock drives narrated tour (caption + mute + skip + first-visit audio hint)"
```

---

## Task 5: 历史消息「▶ 重新解读」（用已存 segments 重演）

**Files:**
- Modify: `frontend/src/components/ziwei/chat-dock/chat-dock.tsx`

历史助手消息若有 `segments`，给一个重演按钮：用 `tour.beginFromSegments` 合成队列 + `tour.play` 重跑编排（不调 AI、不入库）。

- [ ] **Step 1: 加重演函数**

在组件内加：
```tsx
  const replayMessage = (m: ChatMessage) => {
    if (!m.segments || m.segments.length === 0) return;
    abortRef.current?.abort();
    tour.cancel();
    setCaption(null);
    const reduced =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const queue = tour.beginFromSegments(m.segments);
    tour.setMuted(muted);
    void tour.play(queue, {
      chart,
      onFocusBranch,
      onTerm,
      onCaption: setCaption,
      onReveal: () => { /* 历史正文已在气泡，无需改写 */ },
      onTourActiveChange,
      reducedMotion: reduced,
    });
  };
```
说明：历史消息的 `content` 已是全文，`onReveal` 留空避免覆盖。重演只驱动镜头+声音+caption。

- [ ] **Step 2: 在已完成的助手消息上显示按钮**

在 assistant 正文分支（`!m.pending` 且有 `m.segments`）尾部加：
```tsx
                <>
                  {m.content}
                  {m.pending ? <span className="animate-pulse text-violet-300/70">▌</span> : null}
                  {!m.pending && m.segments && m.segments.length > 0 ? (
                    <div className="mt-1">
                      <button type="button" onClick={() => replayMessage(m)} className="text-xs text-violet-300/60 hover:text-violet-100">
                        ▶ 重新解读
                      </button>
                    </div>
                  ) : null}
                </>
```
（替换 Task 4 Step 6 里的那段 `<>{m.content}...</>`。）

- [ ] **Step 3: 历史会话载入时带上 segments**

确认 `handleLoadConversation` 的 `mapped` 来自 `HistoryPanel`，其 `ChatMessage.segments` 取自 `chart_context_json.segments`。检查 `history-panel.tsx` 的映射是否填了 `segments`；若没填，补上 `segments: msg.chart_context_json?.segments`。

Run（先看 history-panel 当前映射）: `grep -n "segments\|chart_context_json\|role:" frontend/src/components/ziwei/chat-dock/history-panel.tsx`
若 assistant 映射未带 `segments`，则补：在构造 assistant `ChatMessage` 处加 `segments: m.chart_context_json?.segments,`。

- [ ] **Step 4: 类型检查**

Run: `cd frontend && npx tsc --noEmit`
Expected: `chat-dock.tsx` / `history-panel.tsx` 无新错误。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ziwei/chat-dock/chat-dock.tsx frontend/src/components/ziwei/chat-dock/history-panel.tsx
git commit -m "feat(ziwei): replay past readings as narrated tour from stored segments"
```

---

## Task 6: 收尾——全量类型检查 + 最终审查 + 部署 + prod 实测

**Files:** 无新增（验证与部署）。

- [ ] **Step 1: 全量类型检查**

Run: `cd frontend && npx tsc --noEmit`
Expected: 仅剩 `scene3d/*` + `camera-rig.tsx` 的**既存** module-resolution 报错（`three`/`@react-three/*`/`camera-controls` 本地未装），无任何业务/类型新错误。

- [ ] **Step 2: 最终整体审查（spec 对照）**

人工或子代理对照 spec §3–§9 逐条核：镜头先动后解说、几乎不显字、结束揭全文、静音/跳过/降级、skip 不 abort 流、历史重演不调 AI。修掉发现的问题。

- [ ] **Step 3: 部署（按 [[deployment_rules]]）**

```bash
git push origin main
git tag v0.38.0
git push origin v0.38.0
gh run watch <run-id> --exit-status
```

- [ ] **Step 4: prod 实测 + 用户确认**

部署绿后：在浏览器打开 portal.leipan.cc/ziwei，问一条，确认——首次出声提示出现一次、声音朗读、镜头慢飞一宫一停、解读期不显大段文字、结束全文落入气泡、🔇 与「直接看文字」可用、历史「▶ 重新解读」可重演。首次解说延迟用 §13 的 PowerShell HttpClient 法量（预期 ~4s 首拍就绪；注意流式 done 总时长仍 ~12s 但表演已开始）。

- [ ] **Step 5: 更新记忆**

更新 `[[ziwei_phase1_progress]]`：记 Phase 3d 叙事化播放上线（版本、感知首拍、关键架构：声音为主时钟/镜头先动后解说/可替换声音源 V2 留云 TTS）。

---

## Self-Review（计划对照 spec）

- **声音源可替换（spec §5）** → Task 1 ✓
- **流式喂指挥器 + 镜头先动后解说（§4）** → Task 2 ✓
- **慢镜头（§7）** → Task 3 ✓
- **解读态 UI/几乎不显字/结束揭全文/默认出声/首次提示（§3、§8）** → Task 4 ✓
- **静音/跳过/降级/skip 不 abort 流（§6、§9）** → Task 2（skip/cancel 语义）+ Task 4（接线）✓。注意：本计划里 skip 走「指挥器内直出」（cancel 当前声音、后续拍直接揭晓），**未 abort 流**——流继续在 `streamOracle` 里跑完触发 onDone→queue.close(convId)，play 收尾落 convId。符合 §6「skip 不 abort」。
- **历史重演（§8 末、§3）** → Task 5 ✓
- **V1 纯前端、后端零改（§2、§12）** → 全计划无后端改动 ✓
- **类型一致性**：`NarrationSource.speak/cancel`、`BeatQueue.push/close/next/convId`、`TourDeps` 字段、`useOracleTour` 返回 `{begin,play,skip,cancel,setMuted,beginFromSegments}`、`ChatDockProps.onTourActiveChange`、`Scene3DProps.tourActive`、`CameraRig.smoothTime` —— 各任务引用一致 ✓
- **占位符扫描**：无 TBD/TODO；每段代码完整 ✓

一个 spec 未尽而计划已处理的点：reduced-motion 在指挥器里等价「直出」（play 循环里 `skippedRef || reducedMotion` 同分支逐拍揭晓），不单独走 streamOracle 的 onText 直铺——效果等价（全文随队列推进揭晓），且复用同一条表演循环，避免两套代码路径。
