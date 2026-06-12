# 紫微解盘 · MiniMax 云端嗓音（V2 声音源）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use `- [ ]`.

**Goal:** 把解盘师的声音从浏览器机械音换成 MiniMax（海螺）云端中文嗓音，并顺手去掉朗读把 `**` 念成「星号」的毛病。

**Architecture:** 后端加一个瘦 `/ziwei/tts` 端点，复用 podcast 已在 prod 验证的 `_tts_bytes()`（T2A v2 → MP3 bytes），密钥只在服务端。前端新增 `CloudNarration` 实现现有 `NarrationSource` 接口：POST 文本→拿 MP3→`HTMLAudioElement` 播放，失败自动回退浏览器语音。所有送进 TTS 的文本先 `stripMarkdown`。指挥器/UI 不动（接口早留好）。

**Tech Stack:** FastAPI + httpx（已用）、MiniMax T2A v2、现有 `podcast_service._tts_bytes`、前端 `HTMLAudioElement` + fetch。

**复用既有事实（已侦察确认）：**
- `backend/app/services/podcast_service.py:336` `_tts_bytes(text, voice_id, api_key, group_id, model="speech-2.6-hd", api_base="https://api.minimax.io") -> bytes`：调 `{api_base}/v1/t2a_v2?GroupId={group_id}`，Bearer 鉴权，hex 解码 MP3，非零 status_code 抛 ValueError。
- `backend/app/core/config.py:25-28` 已有 `minimax_api_key/minimax_group_id/minimax_api_base/minimax_model`。
- `.github/workflows/deploy.yml:93-94` 已 upsert `MINIMAX_API_KEY/MINIMAX_GROUP_ID`；`infra/docker-compose.prod.yml:45-47` 已传 key/group/model。**密钥 podcast 已在用 → 无需新增 provisioning。**
- 有效中文 voice_id 目录见 `podcast_service.py:64-89`（`Chinese (Mandarin)_Radio_Host` 等）。
- 前端 `frontend/src/lib/ziwei/narration.ts` 已有 `NarrationSource`/`BrowserNarration`/`SilentNarration`/`estimateDuration`；`use-oracle-tour.ts` 的 `getNarration()` 现返回 `BrowserNarration`。
- 前端无单测框架；验证 = `tsc --noEmit`（不引入新错）+ CI build + prod。后端有 pytest，按 TDD。

---

## Task A: 后端 `/ziwei/tts` 端点（复用 _tts_bytes）

**Files:**
- Modify: `backend/app/core/config.py`（加 oracle 嗓音设置）
- Modify: `backend/app/api/v1/routes/ziwei.py`（加端点）
- Test: `backend/tests/test_ziwei_tts.py`（新建）

- [ ] **Step 1: config 加 oracle 嗓音设置**

在 `backend/app/core/config.py` 的 minimax 区块（line 28 `minimax_model` 之后）加一行：
```python
    minimax_oracle_voice_id: str = "Chinese (Mandarin)_Radio_Host"  # 解盘师默认嗓音，可经 env MINIMAX_ORACLE_VOICE_ID 覆盖
```

- [ ] **Step 2: 写失败测试 `backend/tests/test_ziwei_tts.py`**

```python
"""Tests for the ziwei TTS proxy endpoint (MiniMax reused, monkeypatched)."""
from __future__ import annotations

import app.api.v1.routes.ziwei as ziwei_routes
from app.core.config import get_settings
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_tts_503_when_no_key(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "minimax_api_key", "", raising=False)
    monkeypatch.setattr(ziwei_routes, "get_settings", lambda: s)
    r = client.post("/api/v1/ziwei/tts", json={"text": "你好"})
    assert r.status_code == 503


def test_tts_returns_mp3_and_strips_markdown(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "minimax_api_key", "k", raising=False)
    monkeypatch.setattr(s, "minimax_group_id", "g", raising=False)
    monkeypatch.setattr(ziwei_routes, "get_settings", lambda: s)
    seen = {}
    def fake_tts(text, voice_id, api_key, group_id, model, api_base):
        seen["text"] = text
        seen["voice_id"] = voice_id
        return b"ID3fakemp3"
    monkeypatch.setattr(ziwei_routes, "_tts_bytes", fake_tts)
    r = client.post("/api/v1/ziwei/tts", json={"text": "你命宫**紫微**坐守"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("audio/mpeg")
    assert r.content == b"ID3fakemp3"
    # markdown 标记被剥掉，不会念成「星号星号」
    assert "**" not in seen["text"] and "紫微" in seen["text"]
    assert seen["voice_id"] == "Chinese (Mandarin)_Radio_Host"


def test_tts_400_empty_text(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "minimax_api_key", "k", raising=False)
    monkeypatch.setattr(ziwei_routes, "get_settings", lambda: s)
    r = client.post("/api/v1/ziwei/tts", json={"text": "   "})
    assert r.status_code == 400


def test_tts_502_on_minimax_error(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "minimax_api_key", "k", raising=False)
    monkeypatch.setattr(s, "minimax_group_id", "g", raising=False)
    monkeypatch.setattr(ziwei_routes, "get_settings", lambda: s)
    def boom(*a, **k):
        raise ValueError("MiniMax TTS error 1004: auth failed")
    monkeypatch.setattr(ziwei_routes, "_tts_bytes", boom)
    r = client.post("/api/v1/ziwei/tts", json={"text": "你好"})
    assert r.status_code == 502
```

- [ ] **Step 3: 跑测试确认失败**

Run: `cd backend && python -m pytest tests/test_ziwei_tts.py -q`
Expected: FAIL（端点不存在 → 404/405，或 import 错误）。

- [ ] **Step 4: 实现端点**

在 `backend/app/api/v1/routes/ziwei.py`：

顶部 import 区加：
```python
import re as _re
from fastapi import Response
from app.services.podcast_service import _tts_bytes
```
（若 `re` 已在文件顶部 import，则复用它，不要重复 import；该文件已 `import re`，所以**不要**再 import `_re`，直接用 `re`。`Response` 从 fastapi 引入——文件已 `from fastapi import APIRouter, Depends, HTTPException`，把 `Response` 加进这一行。）

加一个 markdown 剥离 helper（端点上方）：
```python
_MD_RE = re.compile(r"\*\*|\*|__|_|`|~~|#")

def _strip_markdown(text: str) -> str:
    """去掉 markdown 强调符号，避免 TTS 把 ** 念成「星号星号」。"""
    return _MD_RE.sub("", text).strip()
```

加端点（放在 oracle 端点附近）：
```python
class TtsRequest(BaseModel):
    text: str


@router.post("/tts")
def ziwei_tts(payload: TtsRequest):
    settings = get_settings()
    if not settings.minimax_api_key or not settings.minimax_group_id:
        raise HTTPException(503, "TTS not configured")
    text = _strip_markdown(payload.text or "")[:800]  # 去标记 + 限长防滥用
    if not text:
        raise HTTPException(400, "Empty text")
    try:
        mp3 = _tts_bytes(
            text,
            settings.minimax_oracle_voice_id,
            settings.minimax_api_key,
            settings.minimax_group_id,
            settings.minimax_model,
            settings.minimax_api_base,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("ziwei tts failed")
        raise HTTPException(502, "TTS upstream error") from exc
    return Response(content=mp3, media_type="audio/mpeg", headers={"Cache-Control": "no-store"})
```
说明：`get_settings`、`BaseModel`、`logger`、`re` 这些在 `routes/ziwei.py` 已存在（前几期已 import logging 建了 `logger`，`re` 也在）。若 `get_settings` 未在模块顶层 import，则该文件其它端点是函数内 `from app.core.config import get_settings`——保持一致：在本端点内 `from app.core.config import get_settings` 亦可。但测试 monkeypatch 的是 `ziwei_routes.get_settings`，**因此必须在模块顶层 `from app.core.config import get_settings`**（若尚未有），让端点用模块级名字。请确认并在模块顶层加 `from app.core.config import get_settings`（若已存在则跳过）。

- [ ] **Step 5: 跑测试确认通过**

Run: `cd backend && python -m pytest tests/test_ziwei_tts.py -q`
Expected: 4 passed.

- [ ] **Step 6: 全套回归**

Run: `cd backend && python -m pytest -q 2>&1 | tail -5`
Expected: 之前的全绿数 +4（test_api.py 那 21 个 JSONB-on-SQLite 既存 error 不算）。

- [ ] **Step 7: Commit**

```
git add backend/app/core/config.py backend/app/api/v1/routes/ziwei.py backend/tests/test_ziwei_tts.py
git commit -m "feat(ziwei): /tts endpoint proxying MiniMax voice (reuses podcast _tts_bytes; strips markdown)"
```

---

## Task B: 前端 CloudNarration + stripMarkdown + 接线

**Files:**
- Create: `frontend/src/lib/ziwei/text.ts`
- Modify: `frontend/src/lib/ziwei/narration.ts`
- Modify: `frontend/src/components/ziwei/chat-dock/use-oracle-tour.ts`
- Modify: `frontend/src/components/ziwei/chat-dock/chat-dock.tsx`

- [ ] **Step 1: `text.ts` — stripMarkdown**

```ts
// frontend/src/lib/ziwei/text.ts
/** 去掉 markdown 强调符号：朗读不会念「星号星号」，展示也不显原始符号。 */
export function stripMarkdown(text: string): string {
  return text
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .replace(/__([^_]+)__/g, "$1")
    .replace(/\*([^*]+)\*/g, "$1")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/~~([^~]+)~~/g, "$1")
    .replace(/^\s{0,3}#{1,6}\s+/gm, "")
    .replace(/^\s*[-*+]\s+/gm, "")
    .replace(/[*_`~#]/g, "")
    .trim();
}
```

- [ ] **Step 2: 验证 stripMarkdown（一次性脚本）**

`frontend/scratch-md.mjs`：
```js
const stripMarkdown = (t) => t.replace(/\*\*([^*]+)\*\*/g,"$1").replace(/__([^_]+)__/g,"$1").replace(/\*([^*]+)\*/g,"$1").replace(/`([^`]+)`/g,"$1").replace(/~~([^~]+)~~/g,"$1").replace(/^\s{0,3}#{1,6}\s+/gm,"").replace(/^\s*[-*+]\s+/gm,"").replace(/[*_`~#]/g,"").trim();
console.log(JSON.stringify(stripMarkdown("你命宫**紫微**坐守，*气象*不凡")), "应为 你命宫紫微坐守，气象不凡");
console.log(JSON.stringify(stripMarkdown("# 标题\n- 项目")), "应无 # 和 -");
console.log(JSON.stringify(stripMarkdown("未闭合 **加粗 和 单个 *")), "应无残留星号");
```
Run `node scratch-md.mjs` → 三行确认无残留 `*_#`。删除 `rm scratch-md.mjs`。

- [ ] **Step 3: `narration.ts` — CloudNarration + BrowserNarration 也 strip**

顶部加 import：
```ts
import { API_BASE } from "@/lib/api";
import { stripMarkdown } from "./text";
```
在 `BrowserNarration.speak` 内，把 `const clean = ...` 改为先剥 markdown：把 `speak(text)` 首行的 `if (!BrowserNarration.isSupported() || !text.trim())` 之前插入 `const spoken = stripMarkdown(text);` 并把后续 `new SpeechSynthesisUtterance(text)` 改用 `spoken`、空判断改用 `spoken`。最小改法——替换 speak 方法体为：
```ts
  speak(text: string): Promise<void> {
    const spoken = stripMarkdown(text);
    if (!BrowserNarration.isSupported() || !spoken.trim()) return Promise.resolve();
    this.cancel();
    return new Promise<void>((resolve) => {
      const u = new SpeechSynthesisUtterance(spoken);
      u.lang = "zh-CN";
      u.rate = 0.92;
      const voice = this.pickVoice();
      if (voice) u.voice = voice;
      const settle = () => { this.current = null; this.resolveFn = null; resolve(); };
      u.onend = settle;
      u.onerror = settle;
      this.current = u;
      this.resolveFn = resolve;
      window.speechSynthesis.speak(u);
    });
  }
```

在文件末尾追加 `CloudNarration`：
```ts
/** MiniMax 云端中文嗓音（默认方案）。POST 文本到后端 /ziwei/tts 拿 MP3 播放；
 * 任何失败（未配置 503 / 网络 / 播放）自动回退浏览器语音，绝不卡死指挥器。 */
export class CloudNarration implements NarrationSource {
  private audio: HTMLAudioElement | null = null;
  private controller: AbortController | null = null;
  private resolveFn: (() => void) | null = null;
  private fallback = new BrowserNarration();
  private cloudDisabled = false; // 一旦确认未配置（503）就整场退浏览器，不再无谓请求

  async speak(text: string): Promise<void> {
    const clean = stripMarkdown(text);
    if (!clean.trim()) return;
    if (typeof window === "undefined") return;
    if (this.cloudDisabled) return this.fallback.speak(clean);
    this.cancel();
    const controller = new AbortController();
    this.controller = controller;
    try {
      const res = await fetch(`${API_BASE}/ziwei/tts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: clean }),
        signal: controller.signal,
      });
      if (controller.signal.aborted) return;
      if (!res.ok) {
        if (res.status === 503) this.cloudDisabled = true; // 没配密钥 → 整场退浏览器
        return this.fallback.speak(clean);
      }
      const blob = await res.blob();
      if (controller.signal.aborted) return;
      await this.playBlob(blob);
    } catch (e) {
      if (controller.signal.aborted || (e instanceof DOMException && e.name === "AbortError")) return;
      return this.fallback.speak(clean); // 网络/其它错误 → 退浏览器
    }
  }

  private playBlob(blob: Blob): Promise<void> {
    return new Promise<void>((resolve) => {
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      const settle = () => {
        URL.revokeObjectURL(url);
        if (this.audio === audio) this.audio = null;
        this.resolveFn = null;
        resolve();
      };
      audio.onended = settle;
      audio.onerror = settle;
      this.audio = audio;
      this.resolveFn = resolve;
      void audio.play().catch(settle); // autoplay 被拦等 → 收尾 resolve（用户点过「问」，通常可播）
    });
  }

  cancel(): void {
    this.controller?.abort();
    this.controller = null;
    this.fallback.cancel();
    const a = this.audio;
    this.audio = null;
    if (a) { a.pause(); a.onended = null; a.onerror = null; }
    const r = this.resolveFn;
    this.resolveFn = null;
    r?.();
  }
}
```

- [ ] **Step 4: `use-oracle-tour.ts` — 默认用云端嗓音**

import 改为引入 CloudNarration：
```ts
import { CloudNarration, SilentNarration, type NarrationSource } from "@/lib/ziwei/narration";
```
把 `browserRef` 改成 `cloudRef`（语义即「带回退的主嗓音」）：
- 字段：`const cloudRef = useRef<NarrationSource | null>(null);`
- `getNarration()`：
```ts
  const getNarration = (): NarrationSource => {
    if (mutedRef.current) return silentRef.current;
    if (!cloudRef.current) cloudRef.current = new CloudNarration();
    return cloudRef.current;
  };
```
- 所有原 `browserRef.current?.cancel()`（在 `skip`/`cancel`/`setMuted` 里）改为 `cloudRef.current?.cancel()`。
（其余逻辑不变；CloudNarration 内部自带浏览器回退。）

- [ ] **Step 5: `chat-dock.tsx` — 展示也剥 markdown**

import：`import { stripMarkdown } from "@/lib/ziwei/text";`
助手正文渲染处 `{m.content}` 改 `{stripMarkdown(m.content)}`（assistant 分支那两处：pending-else 的 `{m.content}`；用户气泡 `{m.content}` 不动）。

- [ ] **Step 6: 类型检查**

Run: `cd frontend && npx tsc --noEmit 2>&1 | grep -E "narration.ts|text.ts|use-oracle-tour.ts|chat-dock.tsx"`
Expected: 空（这些文件不 import 3D 库）。`@/lib/api` 的 `API_BASE` 已存在（api.ts 在用）。

- [ ] **Step 7: Commit**

```
git add frontend/src/lib/ziwei/text.ts frontend/src/lib/ziwei/narration.ts frontend/src/components/ziwei/chat-dock/use-oracle-tour.ts frontend/src/components/ziwei/chat-dock/chat-dock.tsx
git commit -m "feat(ziwei): default to MiniMax CloudNarration with browser fallback; strip markdown in speech+display"
```

---

## Task C: 部署 + prod 实测

- [ ] **Step 1: 确认密钥已在 prod**（podcast 能出声=密钥在）。若不确定，部署后测 /ziwei/tts 直接看 200 还是 503。
- [ ] **Step 2: 全量 tsc**：`cd frontend && npx tsc --noEmit 2>&1 | grep "error TS" | grep -vE "scene3d/|camera-rig.tsx|iztro|chart.ts"` → 应空。
- [ ] **Step 3: 部署**（[[deployment_rules]]）：`git push origin main && git tag v0.39.0 && git push origin v0.39.0 && gh run watch <id> --exit-status`。
- [ ] **Step 4: prod 验证**：①`curl/PowerShell POST https://portal.leipan.cc/api/v1/ziwei/tts {"text":"你好"}` → 200 audio/mpeg（确认密钥在、域名对）。②浏览器问一条，确认是 MiniMax 嗓音、不再念「星号」、慢镜头+声音同步、结束脚本干净。
- [ ] **Step 5: 更新 [[ziwei_phase1_progress]]**：记 MiniMax 云端嗓音上线（版本、voice_id、复用 podcast _tts_bytes、CloudNarration 带浏览器回退、markdown strip）。

---

## Self-Review（计划对照需求）
- **MiniMax 中文嗓音替换浏览器音** → Task A 端点 + Task B CloudNarration 默认 ✓
- **`**` 不再念成星号** → 后端 `_strip_markdown` + 前端 `stripMarkdown`（送 TTS 前 + 展示）双保险 ✓
- **密钥只在服务端** → 后端代理，前端只打自家 /ziwei/tts ✓
- **未配置/失败优雅回退** → CloudNarration 503/网络/播放失败均退 BrowserNarration ✓
- **静音不变** → getNarration muted→Silent 不变 ✓
- **复用既有** → _tts_bytes、deploy/compose env、voice 目录全复用，零新基建 ✓
- **类型一致**：`CloudNarration` 实现 `NarrationSource`；`getNarration` 返回类型不变；`stripMarkdown` 签名一致 ✓
- 遗留可选：每段 synth ~1-2s 的静默间隙未做预取（V1 接受，体验若顿挫再加 prefetch）。
