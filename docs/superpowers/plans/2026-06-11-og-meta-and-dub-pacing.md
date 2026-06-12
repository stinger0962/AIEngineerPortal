# OG 分享卡片 + 配音节奏修复 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use `- [ ]`.

**Goal:** (1) 分享蒸馏所链接时显示有意义的标题/描述（Open Graph），不再是空白裸 URL；(2) 修复「配」的配音节奏漂移（A 吃停顿对齐 + B 全局匀速适配 + D 用 MiniMax speed 减少时间拉伸）。

**两部分互不相关、文件不重叠**：Part 1 纯前端 `src/app/**`；Part 2 纯后端 `dub_service.py`/`podcast_service.py`。顺序执行（避免 git index 冲突），先 Part 1 后 Part 2。

---

# Part 1 — Open Graph 分享卡片（第一级：标题+描述，无图）

**背景**：`frontend/src/app/layout.tsx` 只有 title/description、无 `openGraph`，且各工具页是 `"use client"` 不能导出 metadata。修法：根 layout 加 `metadataBase` + 默认 openGraph/twitter；每个工具目录加一个**服务端** `layout.tsx` 导出专属 metadata。

工具身份（标题/描述源自 `toolkits/page.tsx`）：
- 索引 `/toolkits`：蒸馏所 · Distill —「万物皆可蒸馏。一组把视频/网页/文章提炼成你用得上形式的小工具。」
- 炼 Forge `/toolkits/podcast`：蒸馏所 · 炼 —「把一条 YouTube 视频炼成一期中文播客，单人或双人对话、原生普通话配音。」
- 织 Loom `/toolkits/summarize`：蒸馏所 · 织 —「把文本、网页、YouTube 或微信文章织成结构化中文摘要。」
- 录 Scribe `/toolkits/scribe`：蒸馏所 · 录 —「把无字幕 YouTube 视频用 Whisper 录成文字稿，逐字转写可下载。」
- 配 Dub `/toolkits/dub`：蒸馏所 · 配 —「把外语 YouTube 视频配成中文旁白视频，原声压低做背景、配音对齐时间轴。」

## Task P1: 根 metadata + 4 个工具 layout + 索引 layout

**Files:**
- Modify: `frontend/src/app/layout.tsx`
- Create: `frontend/src/app/toolkits/layout.tsx`
- Create: `frontend/src/app/toolkits/podcast/layout.tsx`
- Create: `frontend/src/app/toolkits/summarize/layout.tsx`
- Create: `frontend/src/app/toolkits/scribe/layout.tsx`
- Create: `frontend/src/app/toolkits/dub/layout.tsx`

- [ ] **Step 1: 根 layout 加 metadataBase + 默认 openGraph/twitter**

把 `frontend/src/app/layout.tsx` 的 `metadata` 替换为：
```tsx
export const metadata: Metadata = {
  metadataBase: new URL("https://portal.leipan.cc"),
  title: {
    default: "AI Engineer Portal",
    template: "%s · AI Engineer Portal",
  },
  description: "Personal AI engineer transition operating system",
  openGraph: {
    type: "website",
    siteName: "AI Engineer Portal",
    locale: "zh_CN",
    title: "AI Engineer Portal",
    description: "Personal AI engineer transition operating system",
  },
  twitter: {
    card: "summary",
    title: "AI Engineer Portal",
    description: "Personal AI engineer transition operating system",
  },
};
```
（`import type { Metadata } from "next";` 已在文件顶部。）

- [ ] **Step 2: 工具目录 layout（服务端，仅导出 metadata 透传 children）**

每个文件结构相同，只是文案不同。**注意**：这些 layout 是服务端组件（无 `"use client"`），只导出 metadata + 返回 `children`，不包任何 UI（UI 仍在各自的 client page 里）。

`frontend/src/app/toolkits/layout.tsx`：
```tsx
import type { Metadata, Viewport } from "next";

const title = "蒸馏所 · Distill";
const description = "万物皆可蒸馏。一组把视频、网页、文章提炼成你真正用得上形式的小工具。";

export const metadata: Metadata = {
  title,
  description,
  openGraph: { title, description, type: "website", siteName: "AI Engineer Portal", locale: "zh_CN" },
  twitter: { card: "summary", title, description },
};

export default function ToolkitsLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
```

`frontend/src/app/toolkits/podcast/layout.tsx`：
```tsx
import type { Metadata } from "next";

const title = "蒸馏所 · 炼 Forge";
const description = "把一条 YouTube 视频炼成一期中文播客 —— 单人讲述或双人对话，原生普通话配音。";

export const metadata: Metadata = {
  title,
  description,
  openGraph: { title, description, type: "website", siteName: "AI Engineer Portal", locale: "zh_CN" },
  twitter: { card: "summary", title, description },
};

export default function ForgeLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
```

`frontend/src/app/toolkits/summarize/layout.tsx`（标题「蒸馏所 · 织 Loom」，描述「把文本、网页、YouTube 或微信文章织成结构化中文摘要 —— TL;DR、关键要点与核心收获。」，函数名 `LoomLayout`，其余同上）。

`frontend/src/app/toolkits/scribe/layout.tsx`（标题「蒸馏所 · 录 Scribe」，描述「把无字幕的 YouTube 视频用 Whisper 录成文字稿 —— 原语言逐字转写，可复制下载。」，函数名 `ScribeLayout`）。

`frontend/src/app/toolkits/dub/layout.tsx`（标题「蒸馏所 · 配 Dub」，描述「把外语 YouTube 视频配成中文旁白视频 —— 原声压低做背景，配音对齐时间轴。」，函数名 `DubLayout`）。

- [ ] **Step 3: 类型检查**

Run: `cd frontend && npx tsc --noEmit 2>&1 | grep -E "app/layout|toolkits/.*layout"` → 空。
注意：工具页是 `"use client"`，page 与 layout 在同一路由段共存是允许的（layout 服务端、page 客户端）。若 tsc 报「client page 不能有 metadata」之类——确认 metadata 在 layout（服务端）而非 page。

- [ ] **Step 4: 验证渲染的 OG 标签（构建产物或 dev）**

因本地可能缺依赖跑不起 build，至少确认源码正确；CI `next build` 为准。可选：若本地能 `npm run build` 则构建后 grep `.next` 里是否含 `og:title`。否则跳过，靠 CI + 部署后线上抓取验证。

- [ ] **Step 5: Commit**

```
git add frontend/src/app/layout.tsx frontend/src/app/toolkits/layout.tsx frontend/src/app/toolkits/podcast/layout.tsx frontend/src/app/toolkits/summarize/layout.tsx frontend/src/app/toolkits/scribe/layout.tsx frontend/src/app/toolkits/dub/layout.tsx
git commit -m "feat(toolkits): Open Graph + Twitter card metadata per 蒸馏所 tool (no more blank share cards)"
```

---

# Part 2 — 配音节奏修复（A 吃停顿 + B 全局匀速 + D MiniMax speed）

**背景**：`dub_service.plan_placements` 当前只按「本句时长」算时槽、超长加速（上限 1.25×）、放不下就往后顶 → 快嘴视频漂移累积。`build_voice_track` 用 ffmpeg `atempo` 事后拉伸（>1.15× 发闷）。

**全部可调常量放 dub_service.py 顶部**（盲调，靠用户听感迭代）：
```python
_MAX_TTS_SPEED = 1.30   # B: 全局 MiniMax 语速上限
_MAX_ATEMPO = 1.15      # A: 单句残余加速上限（base 已担全局，故比旧 1.25 更温和）
_CHARS_PER_SEC = 4.8    # 估算：MiniMax 中文旁白 @speed1.0 约 4.8 字/秒
_VOICE_FILL = 0.92      # 语音最多占视频时长的比例，留呼吸
```
（保留旧 `_MAX_SPEED` 名字会混淆——本计划用 `_MAX_ATEMPO` 取代 `plan_placements` 里的 `_MAX_SPEED`；删除旧 `_MAX_SPEED = 1.25` 定义。）

## Task P2a: D — `_tts_bytes` 加 speed 参数（podcast_service）

**Files:**
- Modify: `backend/app/services/podcast_service.py`
- Test: `backend/tests/test_dub_service.py`（加 1 个用例）

- [ ] **Step 1: 写失败测试**（在 `test_dub_service.py` 末尾加）

```python
def test_tts_bytes_passes_speed(monkeypatch):
    import app.services.podcast_service as ps
    captured = {}
    class _Resp:
        def raise_for_status(self): pass
        def json(self): return {"base_resp": {"status_code": 0}, "data": {"audio": "00"}}
    def fake_post(url, headers=None, json=None, timeout=None):
        captured["speed"] = json["voice_setting"]["speed"]
        return _Resp()
    import httpx
    monkeypatch.setattr(httpx, "post", fake_post)
    ps._tts_bytes("你好", "v", "k", "g", "m", "https://api.minimax.io", speed=1.2)
    assert captured["speed"] == 1.2
```
Run `cd backend && python -m pytest tests/test_dub_service.py::test_tts_bytes_passes_speed -q` → FAIL（`_tts_bytes` 无 speed 参数 → TypeError）。

- [ ] **Step 2: 实现**——给 `_tts_bytes` 加 `speed: float = 1.0`，用在 `voice_setting.speed`

在 `backend/app/services/podcast_service.py` 的 `_tts_bytes` 签名末尾加 `speed: float = 1.0,`，把 body 里 `"speed": 1.0,` 改为 `"speed": speed,`。其余不变（默认 1.0 → podcast 调用零影响）。

- [ ] **Step 3: 通过 + 回归**

Run `cd backend && python -m pytest tests/test_dub_service.py -q` → 全绿（含新用例）。

- [ ] **Step 4: Commit**

```
git add backend/app/services/podcast_service.py backend/tests/test_dub_service.py
git commit -m "feat(tts): _tts_bytes accepts speed param (default 1.0; enables dub global pacing)"
```

## Task P2b: A+B — gap-aware 对齐 + 全局匀速

**Files:**
- Modify: `backend/app/services/dub_service.py`
- Test: `backend/tests/test_dub_service.py`

- [ ] **Step 1: 写失败测试**（覆盖 A 与 B 的纯函数）

```python
from app.services.dub_service import plan_placements, estimate_ms, compute_base_speed

def test_estimate_ms_proportional():
    assert estimate_ms("") == 0
    a, b = estimate_ms("六个字六个"), estimate_ms("十二个字十二个字十二")
    assert b > a > 0

def test_compute_base_speed_fits_when_roomy():
    # 短译文 + 长视频 → 不提速
    assert compute_base_speed(["你好"], 60_000) == 1.0

def test_compute_base_speed_speeds_up_when_dense():
    # 极密译文 + 短视频 → 提速但封顶 1.30
    zh = ["这是一段很长很长的中文" * 20]
    g = compute_base_speed(zh, 3_000)
    assert 1.0 < g <= 1.30

def test_plan_placements_uses_following_gap():
    # 句子 0..1s（slot 1s），但下一句要到 5s 才开始 → 2s 的 clip 借用间隙，无需提速
    segs = [{"start": 0.0, "end": 1.0}, {"start": 5.0, "end": 6.0}]
    plans = plan_placements(segs, [2000, 500], video_ms=8000)
    assert plans[0]["ratio"] == 1.0 and plans[0]["pos"] == 0  # 用了 0..5s 的可用窗，不提速
    assert plans[0]["dur"] == 2000

def test_plan_placements_speeds_when_exceeds_gap():
    # clip 6s 但到下一句只有 5s 可用 → 提速 = 6000/5000=1.2，封顶 _MAX_ATEMPO=1.15
    segs = [{"start": 0.0, "end": 1.0}, {"start": 5.0, "end": 6.0}]
    plans = plan_placements(segs, [6000, 500], video_ms=8000)
    assert 1.0 < plans[0]["ratio"] <= 1.15

def test_plan_placements_last_uses_video_end():
    segs = [{"start": 0.0, "end": 1.0}]
    plans = plan_placements(segs, [3000], video_ms=10000)
    assert plans[0]["ratio"] == 1.0  # 到 10s 都可用，3s clip 不提速
```
Run → FAIL（`estimate_ms`/`compute_base_speed` 不存在；`plan_placements` 签名缺 `video_ms`）。

- [ ] **Step 2: 实现**

在 `dub_service.py`：删除 `_MAX_SPEED = 1.25`，按上面「可调常量」加 4 个常量。加两个纯函数 + 重写 `plan_placements`：
```python
def estimate_ms(text: str) -> int:
    """按字数估算中文旁白时长（speed 1.0）。仅用于全局匀速预算，不求精确。"""
    return int(len(text.strip()) / _CHARS_PER_SEC * 1000)


def compute_base_speed(zh_texts: List[str], video_ms: int) -> float:
    """B：全局匀速——译文总估时若超过视频可填时长，统一略微提速以贴合（封顶 _MAX_TTS_SPEED），
    否则 1.0。匀速比「局部猛提速」更自然，也抑制尾部漂移。"""
    total = sum(estimate_ms(t) for t in zh_texts)
    fillable = max(int(video_ms * _VOICE_FILL), 1)
    if total <= fillable:
        return 1.0
    return min(round(total / fillable, 3), _MAX_TTS_SPEED)


def plan_placements(segments: List[Dict], clip_durations_ms: List[int], video_ms: int) -> List[Dict]:
    """A：吃停顿对齐。每句锚定原句 start；可用窗 = 到「下一句 start」（含其后的停顿），
    放不下才用 atempo 提速（封顶 _MAX_ATEMPO）；落后时 pos 被 cursor 顶高、可用窗自然收窄 →
    内建追赶，抑制漂移。最后一句的可用窗到 video_ms。"""
    out: List[Dict] = []
    cursor = 0
    n = len(segments)
    for i, (seg, clip_ms) in enumerate(zip(segments, clip_durations_ms)):
        start_ms = int(seg["start"] * 1000)
        next_start = int(segments[i + 1]["start"] * 1000) if i + 1 < n else video_ms
        pos = max(start_ms, cursor)
        avail = max(next_start - pos, 1)
        ratio = 1.0
        if clip_ms > avail:
            ratio = min(clip_ms / avail, _MAX_ATEMPO)
        final_ms = int(round(clip_ms / ratio))
        out.append({"pos": pos, "ratio": ratio, "dur": final_ms})
        cursor = pos + final_ms
    return out
```

- [ ] **Step 3: 通过**

Run `cd backend && python -m pytest tests/test_dub_service.py -q` → 全绿。

- [ ] **Step 4: Commit**

```
git add backend/app/services/dub_service.py backend/tests/test_dub_service.py
git commit -m "feat(dub): gap-aware placement + global uniform speed (kill drift on fast speakers)"
```

## Task P2c: 接线 build_voice_track（用 base_speed 生成 + 新 plan_placements 签名）

**Files:**
- Modify: `backend/app/services/dub_service.py`

- [ ] **Step 1: 改 `build_voice_track`**

```python
def build_voice_track(
    segments: List[Dict],
    zh_texts: List[str],
    voice_id: str,
    mm_key: str,
    mm_group: str,
    mm_model: str,
    mm_base: str,
    video_ms: int,
) -> "AudioSegment":
    """B：先按全局 base_speed 生成 TTS（匀速、自然）；A：gap-aware 锚定放置，残余才小幅 atempo。"""
    from app.services.podcast_service import _tts_bytes

    base_speed = compute_base_speed(zh_texts, video_ms)
    clips: List[Optional[AudioSegment]] = []
    durations: List[int] = []
    for zh in zh_texts:
        if not zh.strip():
            clips.append(None)
            durations.append(0)
            continue
        data = _tts_bytes(zh, voice_id, mm_key, mm_group, mm_model, mm_base, speed=base_speed)
        clip = AudioSegment.from_file(io.BytesIO(data))
        clips.append(clip)
        durations.append(len(clip))

    plans = plan_placements(segments, durations, video_ms)
    base = AudioSegment.silent(duration=max(video_ms, 1))
    for clip, plan in zip(clips, plans):
        if clip is None:
            continue
        if plan["ratio"] > 1.0:
            clip = _atempo(clip, plan["ratio"])
        base = base.overlay(clip, position=plan["pos"])
    return base
```
（`_atempo` 不变；注意 `plan_placements` 现在三参，调用已带 `video_ms`。）

- [ ] **Step 2: 全套后端回归**

Run `cd backend && python -m pytest -q 2>&1 | tail -6`。确认 dub 测试全绿、无新失败（test_api.py 的 21 个 JSONB 既存 error 不算）。确认没有别处仍以两参调用 `plan_placements`（grep）：
Run `grep -rn "plan_placements(" backend/app backend/tests` → 调用处都应是三参。

- [ ] **Step 3: Commit**

```
git add backend/app/services/dub_service.py
git commit -m "feat(dub): wire global base-speed TTS into voice track build"
```

---

# Part 3 — 部署 + 验证

- [ ] 全量 tsc（前端）：`cd frontend && npx tsc --noEmit 2>&1 | grep "error TS" | grep -vE "scene3d/|camera-rig.tsx|iztro|chart.ts"` → 空。
- [ ] 全套后端测试通过。
- [ ] 部署（[[deployment_rules]]）：`git push origin main && git tag v0.40.0 && git push origin v0.40.0 && gh run watch <id> --exit-status`。
- [ ] 验证 OG：部署后线上抓取 `https://portal.leipan.cc/toolkits/dub` 的 HTML，确认含 `og:title`「蒸馏所 · 配 Dub」+ `og:description`。可用 `curl -s URL | grep -i 'og:'`（注意 SSR/动态渲染——Next 会把 metadata 注入 `<head>`）。
- [ ] 验证配音：用户在线重配那条马斯克讲话，听节奏是否跟手、尾部是否还漂移；据听感调 `_CHARS_PER_SEC`/`_VOICE_FILL`/`_MAX_TTS_SPEED`/`_MAX_ATEMPO`。
- [ ] 更新记忆 [[distill_suite]]：OG 卡片上线 + dub 节奏 A/B/D 改造（可调常量位置、盲调需用户听感迭代）。

---

## Self-Review（计划对照需求）
- **分享卡片显示「蒸馏所 配」等信息** → Part 1 根+5 个 layout 的 openGraph/twitter ✓
- **A 吃停顿** → `plan_placements` 用到下一句 start 的可用窗（含停顿）✓
- **B 全局匀速防漂移** → `compute_base_speed` + 按其生成 TTS ✓
- **D MiniMax speed 替代时间拉伸** → `_tts_bytes` speed 参数 + base_speed 生成；atempo 降为残余小幅（cap 1.15）✓
- **类型/签名一致**：`plan_placements` 三参（含 video_ms）所有调用同步；`_tts_bytes` speed 默认 1.0 向后兼容 podcast；新增 `estimate_ms`/`compute_base_speed` 有测试 ✓
- 盲调风险：所有常量置顶可调，靠用户听感迭代（无法在无音频环境主观验证）✓
