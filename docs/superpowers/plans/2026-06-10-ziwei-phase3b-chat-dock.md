# 紫微斗数 Phase 3b（AI 解盘师 · 沉浸式对话坞）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 Phase 3a 的后端大脑接上沉浸式前端——三态浮动对话坞替换临时探针面板；AI 解读按「段落回放」逐段打字 + 同步驱动 3D 镜头飞入对应宫位（说到哪飞到哪）；术语弹白话卡；人设可切换；历史会话可回看。

**Architecture:** oracle 保持非流式（复用已验证循环，零重写风险），仅**额外返回按轮分组的 `segments`（每段 = 一轮的讲解文字 + 该轮的镜头指令）**。前端新建 `ZiweiWorkspace` 容器上提 `selectedBranch`/术语卡状态，`ChartView` 改为受控；`ChatDock` 三态（收起✦/常规坞/全高展开）；回放引擎逐段打字并按段触发镜头（`focus_palace(宫名)` → 查 `chart.palaces` 得地支 → `setSelectedBranch` → Phase 2 的 CameraRig 自动飞入）。无 SSE、无 AsyncAnthropic。

**Tech Stack:** Next.js 15 + React 19 + R3F（已装）。后端 FastAPI（仅小幅扩 oracle 返回 + 路由 + 持久化）。

**Spec:** `docs/superpowers/specs/2026-06-09-ziwei-3d-design.md`（§3.2 镜头联动、§3.3 对话坞三态与回看、§11 分期第 3 条 3b 部分）

**关键既有接口（侦察确认，照此对接）：**
- 镜头联动落点：`selectedBranch: string|null`（地支）变化 → `CameraRig`（`camera-rig.tsx`）`setLookAt` 飞入。Phase 2 已实现，**不改**。
- 宫名→地支：oracle 的 `focus_palace.palace` 是**宫名**（命宫/官禄…），需 `chart.palaces.find(p=>p.name===palace)?.earthlyBranch` 转地支。
- 镜头指令形态：`{type:"focus_palace",palace}` / `{type:"overview"}` / `{type:"explain_term",term,explanation}`（`oracle_tools.py`）。
- `Scene3DProps`：`{chart, selectedBranch, onSelectBranch, onRenderError?}`（`scene-3d.tsx`，不改）。
- `branchPosition(地支)`、`BRANCH_GRID`（`layout.ts`，不改）。
- 后端 oracle.run 现返回 `{response, camera_commands, _meta}`；路由 `POST /ziwei/profiles/{id}/oracle`、`GET .../conversations`、`GET /ziwei/conversations/{cid}/messages` 已存在。
- api.ts 现有 `askOracle`、`CameraCommand`、`OracleReply`、`OracleAsk`、`ZiweiApiError`、`hasChart`，**缺** listConversations/listMessages（本期加）。
- 视觉词汇：bg `#050310`/`#120a2e`/`#0a0618`；border `violet-500/20~40`；text `violet-100`/`violet-300/70`/`violet-400`；圆角 `rounded-[28px]`/`rounded-[20px]`/`rounded-xl`/`rounded-full`；`backdrop-blur`；按钮 `bg-violet-600`(active)/`bg-violet-600/20`(default)。
- 人设：`PERSONA_LABELS={sage:温和智者,taoist:仙风道骨,analyst:现代分析师}`（`constants.ts`），`profile.persona` 已有；改人设用 `ziweiApi.updateProfile(id,{persona})`。

**约定：** Windows PowerShell（`;`，无 `&&`）；worktree 分支 `worktree-ziwei-phase3b`，只 commit 不 push；后端测试临时 SQLite + mock client（参 `test_ziwei_oracle.py`/`test_ziwei_oracle_routes.py`）；前端无测试框架，用 `npx tsc --noEmit` + `npm run build` + 浏览器实测；drei/R3F props 以 node_modules .d.ts 为准，不许 `any`。

---

### Task 1: 后端 oracle 返回按轮分组的 segments

**Files:**
- Modify: `backend/app/services/ziwei/oracle.py`（`run` 累积 segments）
- Test: `backend/tests/test_ziwei_oracle.py`（加 segments 测试）

**设计：** 每一轮 = 一段「讲解文字 + 该轮镜头指令」。前端按段回放。不动现有 `response`/`camera_commands`（向后兼容探针与持久化），仅新增 `segments`。

- [ ] **Step 1: 改 run** — `backend/app/services/ziwei/oracle.py`。在 `camera_commands`/`text_parts` 旁加 `segments: list[dict] = []`；`_result` 增加 `"segments": segments`；每轮收集本轮 text 与 commands 后 append 一个非空 segment。最终 `run` 体如下（替换现有 run 方法体，保留签名与 `_system_prompt`）：

```python
        system_prompt = self._system_prompt(chart_json, persona, scenario, portrait)
        claude_messages = messages[-10:] if len(messages) > 10 else list(messages)
        camera_commands: list[dict] = []
        text_parts: list[str] = []  # 累积每一轮讲解（模型常「边讲边 focus」，文字与工具同 response）
        segments: list[dict] = []   # 按轮分组：{text, commands}，供前端「段落回放」逐段打字+同步飞镜头
        in_tok = out_tok = 0
        start = time.time()

        def _result(rounds: int) -> dict:
            return {
                "response": "\n\n".join(t for t in (p.strip() for p in text_parts) if t),
                "camera_commands": camera_commands,
                "segments": segments,
                "_meta": {
                    "model": self.model, "input_tokens": in_tok, "output_tokens": out_tok,
                    "total_tokens": in_tok + out_tok, "latency_ms": int((time.time() - start) * 1000),
                    "rounds": rounds,
                },
            }

        for round_num in range(1, max_rounds + 1):
            create_kwargs: dict = dict(
                model=self.model, max_tokens=2200, system=system_prompt,
                messages=claude_messages, timeout=40.0,
            )
            if round_num < max_rounds:
                create_kwargs["tools"] = TOOL_SCHEMAS
            try:
                response = self.client.messages.create(**create_kwargs)
            except Exception:
                return _result(round_num) if text_parts else None
            in_tok += response.usage.input_tokens
            out_tok += response.usage.output_tokens

            round_text = "".join(b.text for b in response.content if b.type == "text" and b.text.strip()).strip()
            if round_text:
                text_parts.append(round_text)
            round_commands: list[dict] = []

            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        out = execute_tool(block.name, block.input)
                        if out.get("ok") and "command" in out:
                            camera_commands.append(out["command"])
                            round_commands.append(out["command"])
                        tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(out, ensure_ascii=False)})
                if round_text or round_commands:
                    segments.append({"text": round_text, "commands": round_commands})
                claude_messages.append({"role": "assistant", "content": response.content})
                claude_messages.append({"role": "user", "content": tool_results})
                continue

            if round_text or round_commands:
                segments.append({"text": round_text, "commands": round_commands})
            return _result(round_num)
        return _result(max_rounds) if text_parts else None
```

- [ ] **Step 2: 加测试** — `backend/tests/test_ziwei_oracle.py` 追加：

```python
def test_oracle_segments_group_text_and_commands_per_round():
    r1 = _fake_response(
        stop_reason="tool_use",
        content=[_fake_text_block("先看官禄宫。"), _fake_tool_use_block("focus_palace", {"palace": "官禄"}, "t1")],
    )
    r2 = _fake_response(
        stop_reason="tool_use",
        content=[_fake_text_block("再看财帛宫。"), _fake_tool_use_block("focus_palace", {"palace": "财帛"}, "t2")],
    )
    r3 = _fake_response(stop_reason="end_turn", content=[_fake_text_block("综上，事业财运俱佳。")])
    client = FakeClient([r1, r2, r3])
    oracle = ZiweiOracle(client=client, model="claude-test")
    result = oracle.run(chart_json=SIMPLE_CHART, persona="sage", scenario="natal", portrait={}, messages=SIMPLE_MESSAGES)

    assert result is not None
    segs = result["segments"]
    assert len(segs) == 3
    assert segs[0]["text"] == "先看官禄宫。"
    assert segs[0]["commands"] == [{"type": "focus_palace", "palace": "官禄"}]
    assert segs[1]["text"] == "再看财帛宫。"
    assert segs[1]["commands"] == [{"type": "focus_palace", "palace": "财帛"}]
    assert segs[2]["text"] == "综上，事业财运俱佳。"
    assert segs[2]["commands"] == []
    # response 仍为全文拼接（向后兼容）
    assert "先看官禄宫" in result["response"] and "综上" in result["response"]
```

- [ ] **Step 3: 运行** — `cd backend; python -m pytest tests/test_ziwei_oracle.py -v` → 全 PASS（原有 6 + 新 1）。

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/ziwei/oracle.py backend/tests/test_ziwei_oracle.py
git commit -m "feat(ziwei): oracle returns per-round segments for synced replay"
```

---

### Task 2: 路由透传并持久化 segments + 前端 API 扩展

**Files:**
- Modify: `backend/app/api/v1/routes/ziwei.py`（响应与 assistant 消息加 segments）
- Test: `backend/tests/test_ziwei_oracle_routes.py`（断言 segments 在响应与 messages）
- Modify: `frontend/src/lib/ziwei/api.ts`（OracleReply 加 segments；加 listConversations/listMessages + 类型）

- [ ] **Step 1: 后端路由** — `routes/ziwei.py` 的 `ask_oracle`：
  1. assistant 消息的 `chart_context_json` 增加 segments：
     ```python
     chart_context_json={"camera_commands": result["camera_commands"], "segments": result.get("segments", []), "scenario": payload.scenario},
     ```
  2. 返回体加 `"segments": result.get("segments", [])`。

- [ ] **Step 2: 后端测试** — `test_ziwei_oracle_routes.py`：在 `test_ask_oracle_creates_conversation_and_persists` 里，让 mock client 返回一个含 text 的 end_turn（已有），断言响应含 `"segments"` 键且为 list；GET messages 时 assistant 的 `chart_context_json` 含 `segments`。运行 `cd backend; python -m pytest tests/test_ziwei_oracle_routes.py -q` 全 PASS。

- [ ] **Step 3: 前端 api.ts** — 追加类型与方法：

```typescript
export type OracleSegment = { text: string; commands: CameraCommand[] };

// OracleReply 增加 segments 字段：
//   segments: OracleSegment[];

export type ConversationOut = { id: number; scenario: string; title: string; created_at: string | null };
export type MessageOut = {
  id: number; role: string; content: string;
  chart_context_json: { camera_commands?: CameraCommand[]; segments?: OracleSegment[]; scenario?: string };
  created_at: string | null;
};

// ziweiApi 增加：
//   listConversations: (profileId) => request<ConversationOut[]>(`/ziwei/profiles/${profileId}/conversations`),
//   listMessages: (conversationId) => request<MessageOut[]>(`/ziwei/conversations/${conversationId}/messages`),
```

把 `OracleReply` 的定义改为含 `segments: OracleSegment[];`（实现者就地修改该 type）。

- [ ] **Step 4: 类型检查** — `cd frontend; npx tsc --noEmit` → 无错误（OracleProbe 仍用旧字段，应不受影响；若 OracleReply 加必填 segments 导致测试型别报错，确保后端 mock 在前端无关——前端无测试，tsc 通过即可）。

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/v1/routes/ziwei.py backend/tests/test_ziwei_oracle_routes.py frontend/src/lib/ziwei/api.ts
git commit -m "feat(ziwei): persist+expose oracle segments, add conversation/message API"
```

---

### Task 3: ZiweiWorkspace 容器 + ChartView 受控化 + 术语卡

**Files:**
- Create: `frontend/src/components/ziwei/ziwei-workspace.tsx`
- Modify: `frontend/src/components/ziwei/chart-view.tsx`（selectedBranch 改为受控 props）
- Create: `frontend/src/components/ziwei/term-card.tsx`
- Modify: `frontend/src/app/ziwei/page.tsx`（`<ChartView>`+`<OracleProbe>` → `<ZiweiWorkspace>`）

**设计：** `selectedBranch` 与术语卡状态上提到 `ZiweiWorkspace`，它同时持有 `ChartView`（受控）与（Task 4 起的）`ChatDock`。本任务先接 ChartView + 术语卡 + 暂时把 OracleProbe 挪进来占位（Task 4 替换）。

- [ ] **Step 1: ChartView 受控化** — 把 `selectedBranch` state 从 ChartView 移除，改为 props `{ chart, selectedBranch, onSelectBranch }`。具体：
  - 删除 `const [selectedBranch, setSelectedBranch] = useState<string|null>(null);`，改由 props 传入。
  - `prevChart` 那段「档案切换重置选宫」移除（改由 workspace 在 profile 变化时重置）。
  - `switchMode` 内 `setSelectedBranch(null)` → `onSelectBranch(null)`。
  - Esc 监听里 `setSelectedBranch(null)` → `onSelectBranch(null)`。
  - 返回总览按钮 `onClick={() => onSelectBranch(null)}`。
  - `<Scene3D ... onSelectBranch={onSelectBranch} />`。
  - 保留 webgl/mode/renderFailed 内部 state 不变。
  - 导出签名：`export function ChartView({ chart, selectedBranch, onSelectBranch }: { chart: ZiweiChart; selectedBranch: string | null; onSelectBranch: (b: string | null) => void })`。

- [ ] **Step 2: 术语卡组件** — `frontend/src/components/ziwei/term-card.tsx`：

```tsx
"use client";

export type TermInfo = { term: string; explanation: string };

export function TermCard({ info, onClose }: { info: TermInfo; onClose: () => void }) {
  return (
    <div className="absolute bottom-4 left-4 z-20 max-w-xs rounded-2xl border border-violet-400/40 bg-[#160b38]/95 p-4 shadow-[0_8px_30px_rgba(91,33,182,0.45)] backdrop-blur">
      <div className="mb-1 flex items-start justify-between gap-3">
        <span className="text-sm font-semibold tracking-wide text-amber-200">{info.term}</span>
        <button type="button" onClick={onClose} aria-label="关闭释义" className="text-violet-300/60 hover:text-violet-100">
          ✕
        </button>
      </div>
      <p className="text-xs leading-relaxed text-violet-200/85">{info.explanation}</p>
    </div>
  );
}
```

- [ ] **Step 3: ZiweiWorkspace** — `frontend/src/components/ziwei/ziwei-workspace.tsx`：

```tsx
"use client";

import { useEffect, useState } from "react";
import { ChartView } from "./chart-view";
import { OracleProbe } from "./oracle-probe"; // Task 4 替换为 ChatDock
import { TermCard, type TermInfo } from "./term-card";
import type { ZiweiProfileOut } from "@/lib/ziwei/api";
import { hasChart } from "@/lib/ziwei/api";

export function ZiweiWorkspace({ profile }: { profile: ZiweiProfileOut }) {
  const [selectedBranch, setSelectedBranch] = useState<string | null>(null);
  const [term, setTerm] = useState<TermInfo | null>(null);

  // 档案切换时回到总览、清术语卡
  useEffect(() => {
    setSelectedBranch(null);
    setTerm(null);
  }, [profile.id]);

  if (!hasChart(profile)) return null;
  const chart = profile.chart_json;

  return (
    <div className="relative">
      <ChartView chart={chart} selectedBranch={selectedBranch} onSelectBranch={setSelectedBranch} />
      {term ? <TermCard info={term} onClose={() => setTerm(null)} /> : null}
      <OracleProbe profileId={profile.id} />
    </div>
  );
}
```

（注：本任务术语卡状态先挂着，Task 5 回放引擎才会 setTerm；OracleProbe 仍在，Task 4 换成 ChatDock 并把 `chart`/`onSelectBranch`/`onTerm` 传进去。）

- [ ] **Step 4: 接入 page.tsx** — 把右侧 `<><ChartView .../>{selected && <OracleProbe .../>}</>` 整段替换为 `<ZiweiWorkspace profile={selected} />`（仅当 `chart` 存在、`selected` 非空）。删除 page.tsx 里对 ChartView/OracleProbe 的直接 import（改 import ZiweiWorkspace）。

- [ ] **Step 5: 验证** — `cd frontend; npx tsc --noEmit; npm run build` 均无错误，`/ziwei` 在路由表。

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/ziwei/ziwei-workspace.tsx frontend/src/components/ziwei/chart-view.tsx frontend/src/components/ziwei/term-card.tsx frontend/src/app/ziwei/page.tsx
git commit -m "feat(ziwei): lift selectedBranch to workspace, controlled ChartView, term card"
```

---

### Task 4: 三态对话坞外壳（收起✦ / 常规坞 / 全高展开）

**Files:**
- Create: `frontend/src/components/ziwei/chat-dock/chat-dock.tsx`
- Create: `frontend/src/components/ziwei/chat-dock/types.ts`
- Modify: `frontend/src/components/ziwei/ziwei-workspace.tsx`（OracleProbe → ChatDock）

**设计：** 本任务建对话坞的**三态外壳与消息收发**（先一次性显示回复，不做回放——回放是 Task 5）。三态：
- `collapsed`：右下角发光 ✦ 小球。
- `normal`：浮动坞（约 360px 宽），显示最近消息 + 输入框 + 人设入口（人设切换 Task 6）。
- `expanded`：从右侧滑出全高面板，可滚动全部消息 + 历史入口（历史 Task 7）。

- [ ] **Step 1: 类型** — `chat-dock/types.ts`：

```tsx
import type { CameraCommand, OracleSegment } from "@/lib/ziwei/api";

export type DockState = "collapsed" | "normal" | "expanded";

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  segments?: OracleSegment[];
  cameras?: CameraCommand[];
  pending?: boolean; // 回放中
};
```

- [ ] **Step 2: ChatDock 外壳** — `chat-dock/chat-dock.tsx`。要点：
  - props：`{ profileId: number; persona: string; chart: ZiweiChart; onFocusBranch: (branch: string | null) => void; onTerm: (t: TermInfo | null) => void }`。
  - state：`dock: DockState`（初始 normal）、`input`、`loading`、`error`、`messages: ChatMessage[]`、`conversationId: number | null`。
  - profileId 变化时重置会话（清 messages/conversationId/error）。
  - `handleSend`：把 user 消息推入 messages；调 `ziweiApi.askOracle(profileId,{scenario:"natal",message,conversation_id})`；成功后 setConversationId；推入 assistant 消息（本任务直接 content=reply.response 一次性显示，segments/cameras 存着备 Task 5 用）；错误用 ZiweiApiError 映射（503/429/其他，文案同 OracleProbe）。loading 期间显示「解盘师凝神观盘……」。
  - 三态渲染：
    - collapsed：`fixed`/`absolute` 右下 ✦ 圆钮，点击 → normal。
    - normal：右下浮动卡（`absolute bottom-4 right-4 w-[340px]`），顶栏含标题「✦ 解盘师」+ 展开钮（→expanded）+ 收起钮（→collapsed）；消息区显示最近 ~4 条（`max-h` 滚动）；底部输入行（textarea + 发送，Enter 发送 Shift+Enter 换行）。
    - expanded：右侧全高面板（`fixed right-0 top-0 h-full w-[380px]` 或在容器内 `absolute inset-y-0 right-0`），顶栏含标题 + 历史入口占位 + 收起到 normal；全消息滚动区；底部输入行。
  - 视觉：`bg-[#120a2e]/95`、`border-violet-500/30`、`backdrop-blur`、`rounded-[20px]`、user 气泡 `bg-violet-600/30 self-end`、assistant `text-violet-100 whitespace-pre-wrap`。
  - 移动端：normal 坞改为底部抽屉宽度自适应（`w-[min(340px,90vw)]`）；expanded 全屏宽（`w-full sm:w-[380px]`）。
  - 可达性：✦ 钮 `aria-label="展开解盘师"`；状态切换钮带 aria-label。

  完整实现交给实现者（按上述 state 机与三态布局），保持与现有 violet 暗色一致；**本任务不做打字回放，assistant 直接整段显示**。

- [ ] **Step 3: workspace 接入** — `ziwei-workspace.tsx`：把 `<OracleProbe .../>` 换成：

```tsx
<ChatDock
  profileId={profile.id}
  persona={profile.persona}
  chart={chart}
  onFocusBranch={setSelectedBranch}
  onTerm={setTerm}
/>
```

删除 OracleProbe import（OracleProbe 文件保留不删，避免误伤，但不再引用）。

- [ ] **Step 4: 验证** — tsc + build 通过；浏览器：进 /ziwei 见右下解盘师坞，可输入提问、整段显示回复，可在 收起/常规/展开 三态间切换。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ziwei/chat-dock/ frontend/src/components/ziwei/ziwei-workspace.tsx
git commit -m "feat(ziwei): three-state chat dock shell with message send"
```

---

### Task 5: 段落回放引擎（逐段打字 + 同步飞镜头 + 术语卡）

**Files:**
- Create: `frontend/src/components/ziwei/chat-dock/use-segment-replay.ts`
- Modify: `frontend/src/components/ziwei/chat-dock/chat-dock.tsx`（用回放替换整段显示）

**设计：** assistant 回复到达后，不直接整段显示，而是「回放」：对 `reply.segments` 逐段——先把该段 `text` 逐字（或分块）追加到该条消息的可见内容，文字铺完后**触发该段的 commands**（`focus_palace`→查宫名得地支→`onFocusBranch(地支)`；`overview`→`onFocusBranch(null)`；`explain_term`→`onTerm({term,explanation})`），停顿后进入下一段。尊重 `prefers-reduced-motion`：减少动态时跳过打字、瞬间显示全文并顺序触发镜头。

- [ ] **Step 1: 回放 hook** — `use-segment-replay.ts`：

```tsx
"use client";

import { useCallback, useRef } from "react";
import type { CameraCommand, OracleSegment } from "@/lib/ziwei/api";
import type { ZiweiChart } from "@/lib/ziwei/types";
import type { TermInfo } from "../term-card";

type ReplayDeps = {
  chart: ZiweiChart;
  onText: (full: string) => void;            // 累进文本回调（更新该条消息可见内容）
  onFocusBranch: (branch: string | null) => void;
  onTerm: (t: TermInfo | null) => void;
  reducedMotion: boolean;
};

const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

function branchOf(chart: ZiweiChart, palaceName: string): string | null {
  return chart.palaces.find((p) => p.name === palaceName)?.earthlyBranch ?? null;
}

export function useSegmentReplay() {
  const cancelRef = useRef(false);

  const cancel = useCallback(() => {
    cancelRef.current = true;
  }, []);

  const fireCommand = (cmd: CameraCommand, deps: ReplayDeps) => {
    if (cmd.type === "focus_palace") {
      const branch = branchOf(deps.chart, cmd.palace);
      if (branch) deps.onFocusBranch(branch);
    } else if (cmd.type === "overview") {
      deps.onFocusBranch(null);
    } else if (cmd.type === "explain_term") {
      deps.onTerm({ term: cmd.term, explanation: cmd.explanation });
    }
  };

  const play = useCallback(async (segments: OracleSegment[], deps: ReplayDeps) => {
    cancelRef.current = false;
    let acc = "";
    for (const seg of segments) {
      if (cancelRef.current) break;
      const text = seg.text ?? "";
      if (deps.reducedMotion || text.length === 0) {
        acc += (acc ? "\n\n" : "") + text;
        deps.onText(acc);
      } else {
        acc += acc ? "\n\n" : "";
        // 分块打字：每 ~2 字一帧
        for (let i = 0; i < text.length; i += 2) {
          if (cancelRef.current) break;
          acc += text.slice(i, i + 2);
          deps.onText(acc);
          await sleep(18);
        }
      }
      if (cancelRef.current) break;
      // 文字铺完，触发该段镜头
      for (const cmd of seg.commands) fireCommand(cmd, deps);
      if (!deps.reducedMotion) await sleep(650); // 段间停顿，让镜头飞到位
    }
    // 收尾：确保全文完整
    const full = segments.map((s) => s.text).filter(Boolean).join("\n\n");
    deps.onText(full);
  }, []);

  return { play, cancel };
}
```

（实现者：`ZiweiChart` 从 `@/lib/ziwei/types` 导入；`CameraCommand`/`OracleSegment` 从 `@/lib/ziwei/api` 导入；上面 import 行按实际修正，勿留错误导入。`TermInfo` 从 `../term-card`。）

- [ ] **Step 2: 接入 ChatDock** — `handleSend` 成功后：
  - 推入一条 `pending` 的 assistant 消息（content 初始空）。
  - `const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;`
  - 调 `replay.play(reply.segments && reply.segments.length ? reply.segments : [{text: reply.response, commands: reply.camera_commands}], { chart, onText: (full)=>更新该条消息 content, onFocusBranch, onTerm, reducedMotion: reduced })`。
  - `onText` 用消息 id 定位并 setMessages 更新该条 content；回放结束清 pending。
  - 发送新消息或切档案时 `replay.cancel()`，避免上一条回放串台。
  - 历史消息（Task 7 载入的）直接整段显示，不回放。

- [ ] **Step 3: 验证** — 浏览器实测（需后端+key，controller 做）：问「事业方向？」→ 文字逐段打出、镜头随讲解依次飞入官禄/财帛等宫、术语弹白话卡、段间停顿自然；开启系统「减少动态」→ 文字瞬显、镜头顺序到位不打字。tsc + build 通过。

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/ziwei/chat-dock/
git commit -m "feat(ziwei): segment replay - typed narration synced with camera fly-ins"
```

---

### Task 6: 人设切换

**Files:**
- Create: `frontend/src/components/ziwei/chat-dock/persona-switch.tsx`
- Modify: `frontend/src/components/ziwei/chat-dock/chat-dock.tsx`（嵌入人设切换）
- Modify: `frontend/src/app/ziwei/page.tsx`（updateProfile 后刷新 profiles 状态，使 persona 变更生效）

- [ ] **Step 1: persona-switch 组件** — 三选一（PERSONA_LABELS），当前值高亮，点击调 `ziweiApi.updateProfile(profileId,{persona})` 并回调上层更新。小巧、暗色风格，可放对话坞顶栏或展开态。props：`{ profileId, persona, onChanged: (next: string) => void }`。切换中禁用、失败回滚。

- [ ] **Step 2: 接入 ChatDock** — 在 normal/expanded 顶栏放人设切换；persona 变更后，新提问即用新人设（后端按 `profile.persona` 取 prompt，故需 page.tsx 的 profiles 状态同步——见 Step 3）。可在切换成功后清空当前会话上下文（提示「已切换人设，将开启新对话」）或仅影响后续提问（择一，简单起见仅影响后续，并把 conversationId 置 null 让下次新开会话）。

- [ ] **Step 3: page.tsx 状态同步** — ChatDock 的 onChanged 冒泡到 page，`setProfiles(prev => prev.map(p => p.id===id ? {...p, persona: next} : p))`，使 `selected.persona` 实时更新传给 workspace/dock。

- [ ] **Step 4: 验证** — 切人设 → 再提问 → 后端用新人设（仙风道骨会半文半白、称「命主」；现代分析师用「倾向性」等词）。tsc + build 通过。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ziwei/chat-dock/persona-switch.tsx frontend/src/components/ziwei/chat-dock/chat-dock.tsx frontend/src/app/ziwei/page.tsx
git commit -m "feat(ziwei): persona switcher wired to profile update"
```

---

### Task 7: 历史会话回看

**Files:**
- Create: `frontend/src/components/ziwei/chat-dock/history-panel.tsx`
- Modify: `frontend/src/components/ziwei/chat-dock/chat-dock.tsx`（展开态接历史）

- [ ] **Step 1: history-panel** — 展开态顶部「历史会话」入口，点击列出该档案过往会话（`ziweiApi.listConversations(profileId)`，按 scenario 分组或时间倒序）；点某会话 → `ziweiApi.listMessages(conversationId)` 载入其全部消息**整段显示**（不回放），并把 conversationId 设为当前，可「从这里继续聊」。props：`{ profileId, onLoad: (conversationId, messages) => void }`。

- [ ] **Step 2: 接入 ChatDock** — 展开态可在「当前对话」与「历史列表」间切；载入历史会话时把其 messages 映射为 ChatMessage[]（assistant 的 segments 可从 `chart_context_json.segments` 取但**不回放**，直接 content 显示）。继续聊则沿用该 conversationId。

- [ ] **Step 3: 验证** — 提问几轮 → 收起再展开 → 历史里看到本次会话 → 点开能看到完整往来 → 继续提问接在同一会话。tsc + build 通过。

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/ziwei/chat-dock/history-panel.tsx frontend/src/components/ziwei/chat-dock/chat-dock.tsx
git commit -m "feat(ziwei): conversation history review in expanded dock"
```

---

### Task 8: 打磨——加载态、移动端、清理探针

**Files:**
- Modify: chat-dock 相关（加载态/移动端）
- Delete: `frontend/src/components/ziwei/oracle-probe.tsx`（已被 ChatDock 取代）

- [ ] **Step 1: 加载态** — 提问后到首段回放前，对话坞显示评意 loading（如「解盘师凝神观盘……」+ 脉冲），避免 10-30s 空白。
- [ ] **Step 2: 移动端核对** — normal 坞 `w-[min(340px,90vw)]`、expanded `w-full sm:w-[380px]`；3D 容器与对话坞不互相遮挡关键区；✦ 钮触达 ≥40px。370px 视口下可用。
- [ ] **Step 3: 删除探针** — 删 `oracle-probe.tsx`（确认无引用：page 与 workspace 已不再 import）。
- [ ] **Step 4: 验证** — tsc + build 通过；`/ziwei` 路由仍在；grep 确认无 oracle-probe 残留 import。
- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat(ziwei): dock loading state, mobile polish, remove probe panel"
```

---

### Task 9: 收尾——全量验证 + E2E + 最终审查

- [ ] **Step 1: 全量验证**
```
cd backend; python -m pytest tests/ --ignore=tests/test_api.py -q     → 全 PASS
cd frontend; npx tsc --noEmit                                          → 无错误
cd frontend; npm run build                                             → 无错误，/ziwei 在路由表
```

- [ ] **Step 2: E2E（controller 用 preview 工具，需后端+真 key）** — 选档案 → 默认 3D 星盘 + 右下解盘师坞 → 问「事业方向？」→ 文字逐段打出、镜头依次飞入对应宫、术语弹卡 → 切人设再问体感不同 → 收起/展开/历史回看 → 切 2D 不崩 → 减少动态偏好下瞬显+顺序镜头。

- [ ] **Step 3: 提交遗留 + 汇报**
```bash
git status; git add -A; git commit -m "chore(ziwei): phase 3b final polish"
```
汇报：测试结果、E2E 情况、与计划偏差。

---

## 后续阶段（不在本计划）

- Phase 4：记忆蒸馏（会话结束异步把要点蒸馏进 `portrait_json`）+ ZiweiLifeEvent 人生事件跟踪验证。
- Phase 5：流年（时间轴）+ 合盘（两盘并列）+ 报告（结构化存档）。
- 可选 3c：真 SSE token 流式（AsyncAnthropic），把「生成期等待」也变成逐字（当前段落回放已覆盖「说到哪飞到哪」的核心体验）。
