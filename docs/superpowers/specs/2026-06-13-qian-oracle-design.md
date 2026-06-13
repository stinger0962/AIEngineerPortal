# 灵签 · 3D 求签 + AI 解签 设计

日期：2026-06-13
状态：已和用户敲定，待写实现计划
所属：算命板块新成员（与紫微斗数并列的独立侧边栏板块）

## 1. 背景与动机

紫微斗数板块（含 3D 星盘 + AI 解盘 + 流式 + 叙事化播放 + MiniMax 配音）已成熟上线。用户想加一个**寺庙求签**式占卜：3D 摇签筒，用户问一个问题/感兴趣的话题，摇出一支签，AI 给出解签。

与紫微不同体系、不同数据，但**底座几乎全可复用**（3D 工具链、AI oracle 单次内联标记、SSE 流式、叙事化播放指挥器、CloudNarration/MiniMax、术语卡、历史模式、侧边栏注册）。新增主要是：一套签文语料、服务端抽签、解签 prompt/人设、一个 3D 摇签筒场景。

## 2. 目标 / 非目标

**目标（V1）**
- 观音灵签 **100 签** 语料（公版核对后入库）。
- **极简仪式**：输入问题 → 摇签 → 掉出一支签 → AI 解签。
- **独立侧边栏板块「灵签」**，共享紫微的 3D/AI/语音底座。
- 解签**单一人设「解签人/庙祝」**（温厚、含蓄、劝人向善）。
- **复用叙事化播放 + MiniMax 配音**：摇出签后镜头推近签文，嗓音念签诗 + 解签。
- 服务端 `secrets` 随机抽签（可审计）；签诗为公版，AI 只解读不杜撰。
- 历史「我的灵签」可回看/重听。
- 配色与门户整体协调（见 §8）。

**非目标（V1）**
- 不做掷筊杯确认仪式（留扩展）。
- 不做关帝/月老/黄大仙等其他签系（留扩展）。
- 不做摇手机/拖拽交互——点按钮自动播摇签动画（留扩展）。
- 不做签文的逐项预制指引（功名/婚姻/疾病…）——这正是 AI 解签按问题现场生成的活。
- 不做物理引擎签筒（canned 动画即可）。

## 3. 体验流程

1. 进入 `/qian`，3D 签筒静置于场景中央（香火/庙宇氛围）。
2. 用户在输入框写下问题或关心的话题（如「今年事业」「这段感情」）。
3. 点「摇签」→ 播**摇晃动画**（签筒晃动、签条碰撞）→ 一支签**升起/掉出**。
4. 揭示该签：**签号 + 吉凶（上上/中平/下下…）+ 签诗四句**。
5. **AI 解签流式展开 + 叙事化播放**：镜头推近签文，解签人嗓音念签诗、再结合用户问题逐句解读；术语卡浮出生僻词白话。解读期屏上极简，结束后整篇解签文落入面板。
6. 存入「我的灵签」历史，可回看/▶ 重听。

**首次进页面**：一次性轻提示「🔊 解签将有声朗读，可随时静音」（复用 ziwei 的 localStorage 提示模式）。

## 4. 数据：观音灵签 100 签

`backend/app/services/qian/signs.py`（Python 常量；或同目录 JSON 资源）。每签：

```python
{
  "id": 1,              # 1..100
  "grade": "上上",       # 吉凶等级：上上/上吉/上/中吉/中平/中/下/下下（按语料归一）
  "palace": "子宫",      # 宫位
  "title": "钟离成道",    # 典故名
  "poetry": "开天辟地作良缘。吉日良时万物全。若得此签非小可。人行忠正帝王宣。",  # 签诗（四句，公版原文）
  "meaning": "此卦盘古初开天地之象，诸事皆吉也。",  # 解曰
  "holy": "急速兆速，年未值时；观音降笔，先报君知。",  # 圣意
}
```

**来源与核对**：以公版语料为底（GitHub `snjor-kii/guanyinqiuqian` 的 100 签 `lottery-data.js` 做基线，字段对应 id/title/type→grade+palace/poetry/meaning/holy），**多源核对签诗与吉凶等级准确性**后入库；只取公版诗文，不抄任何站点私加注解。100 条齐全是 V1 验收门槛。

## 5. 后端架构（镜像 ziwei oracle，去掉排盘）

新目录 `backend/app/services/qian/`：
- `signs.py`：100 签语料 + `get_sign(id)` / `all_signs()`。
- `draw.py`：`draw_sign() -> sign` 用 `secrets.choice` 服务端随机抽签（公平、可审计，不靠前端随机）。
- `personas.py`：解签人单人设 system prompt 片段（温厚庙祝，劝善、含蓄、不武断；给希望也给提醒）。
- `oracle.py`：`QianOracle.run/stream`——把 **签诗 + 吉凶 + 解曰 + 圣意 + 用户问题 + 解签人设** 组装成 system+message，单次 Claude 调用、内联镜头/术语标记（**复用 `ziwei/oracle_tools.py` 的 `parse_markers`/`StreamMarkerParser`**，标记集精简见 §7）。

路由 `backend/app/api/v1/routes/qian.py`：
- `POST /qian/oracle/stream`：body `{question: str, sign_id?: int, persona?: str}`。无 sign_id 则服务端 `draw_sign()`；流式吐 `{type:"sign", sign:{...}}`（先把抽到的签发给前端揭示）+ 随后 `{type:"text"|"camera"|"done"|"error"}`（复用 ziwei 流式协议）。预算守卫复用。本端点只产出文本+签+镜头标记，不产音频。
  - **TTS 复用**：解签朗读复用现有 `/ziwei/tts`（它只是「文本→MiniMax MP3」，与紫微逻辑无耦合）——前端 `CloudNarration` 已指向它，逐段念。V1 直接复用此端点、不新增；命名中性化为 `/tts` 留作可选清理。
- `GET /qian/readings` + `GET /qian/readings/{id}`（或 messages 风格）：历史列表/详情。
- 持久化：新表 `QianReading`（id, question, sign_id, grade, response(解签全文), camera_commands/segments_json, created_at）。沿用 ziwei 的「流式 done 后用 fresh session 持久化 + AIFeedback 计 token」模式。

## 6. 前端架构（`/qian` 页 + 侧边栏「灵签」）

- 侧边栏 `sidebar-nav.tsx` 注册「灵签」入口（图标 + 路由 `/qian`）。
- `frontend/src/app/qian/page.tsx` + `frontend/src/components/qian/`：
  - `qian-workspace.tsx`：持有 `drawnSign`/`tourActive`/术语卡状态（镜像 ziwei-workspace）。
  - `scene3d/`：**新签筒场景**——`Canvas`（dynamic ssr:false）+ 签筒 mesh + 签条 + 摇晃动画（canned，用 `1-exp(-k·dt)` 帧无关过渡或关键帧）+ 一支签升起 + 香火氛围光。复用 ziwei 的 WebGL 检测/2D 回退/context-loss 善后模式；2D 回退 = 直接文字揭签。
  - `draw-panel.tsx`：问题输入 + 「摇签」按钮 + 揭签卡（签号/吉凶/签诗）+ 解签流式面板。
  - 解签播放**复用**：`useOracleTour` 指挥器、`CloudNarration`、术语卡。注意：`useOracleTour`/`fireCamera` 现绑定 ziwei 的「宫位→地支」镜头落点；求签镜头落点不同（推近签文/总览），故**把镜头执行抽象出来**——指挥器保持通用（节拍队列 + 镜头先动后解说），`fireCamera` 改为接收一个由调用方注入的「镜头执行器」(focus-sign / overview / term)。这是对现有 `camera.ts` 的一次小重构，让紫微与求签各注入自己的落点逻辑。
  - `qianApi.streamOracle`（镜像 ziwei 的 `streamOracle`，打 `/qian/oracle/stream`；新增 `onSign` 事件处理揭签）。
  - 历史面板「我的灵签」（镜像 ziwei history-panel）。

## 7. 镜头 / 标记联动（轻量）

求签 3D 比紫微简单（无十二宫）。标记集精简为：
- `[[focus:sign]]`：镜头推近签文/签条。
- `[[overview]]`：拉回签筒全景。
- `[[term:词|释]]`：解释签诗里的生僻词/典故（复用术语卡）。

解签 prompt 指示模型：开篇推近签文念签诗，再结合问题逐句解读，关键古词用 term 标记，2-3 处镜头即可。复用 `StreamMarkerParser` 与叙事化播放，无需新机制。

## 8. 视觉与配色（与门户协调）

求签是**寺庙/观音**主题，配色取「**庙宇暖金 + 赭/朱**」，落在**偏暖的深色底**上——既有香火庙宇的庄重温润，又与门户的 ember 暖色家族呼应，且与紫微的**冷紫**明确区分（两个占卜板块各有色相身份）。建议色板：
- 底色：偏暖近黑 `#140e08`（vs 紫微的冷 `#050310`）。
- 主点缀：**庙宇金/铜** `#d6a84a`（香火、铜炉、签牌）。
- 次点缀：**朱红/赭** `#b9472f`（庙宇朱漆，少量用于吉凶高亮、强调）。
- 文字：暖白 `#f4ece0` / 柔灰金。
- 吉凶等级用色温映射：上上/上吉偏金、中平偏暖灰、下下偏赭——克制、不刺眼。
- 蒸馏所工具页是亮色卡片体系，与求签的沉浸 3D 是两种语境，不强行统一；只要求签自身与门户「暖色家族 + 高质感深色沉浸」基调一致。
最终观感由用户在浏览器确认（前端无单测框架，靠 tsc + build + 肉眼）。

## 9. 随机与公平

服务端 `secrets.choice(all_signs())` 抽签——加密级随机、可审计，不依赖前端。3D 摇签动画是**装饰**；真正的签由服务端返回（前端拿到 sign 后让对应签升起/揭示）。

## 10. 复用清单

| 复用现成 | 新建 |
|---|---|
| R3F 3D 工具链/Canvas/相机基础、WebGL 检测+2D 回退、SSE 流式协议、`oracle_tools` 的 `parse_markers`/`StreamMarkerParser`、叙事化播放指挥器 `useOracleTour`、`CloudNarration`(MiniMax via `/ziwei/tts`)、术语卡、历史面板模式、预算守卫、流式 done 持久化模式、侧边栏注册、首次出声提示 | 100 签语料 `signs.py`、`draw.py`(secrets 抽签)、解签 `oracle.py`+`personas.py`、路由 `qian.py`+`/qian/oracle/stream`(含 `onSign`)、`QianReading` 表、`/qian` 页与 `components/qian/*`、3D 签筒场景+摇签动画、`camera.ts` 镜头执行器抽象（让两板块各注入落点）|

## 11. 边界 / 免责 / 错误处理

- 娱乐向免责声明（同紫微，页面注明）。
- 解签需 `ANTHROPIC_API_KEY`（prod 已有）；超预算返回 429，前端本地化提示。
- 流式中途失败：复用 ziwei 的 salvage + error 帧；前端保留已得文本。
- 语音不可用 / reduced-motion：复用 CloudNarration 浏览器回退 + 指挥器降级「直出文字」。
- 签诗为公版原文；AI 输出仅解读，prompt 明确「不得改写或臆造签诗」。

## 12. 测试

- 后端（pytest，TDD）：`draw_sign` 命中 1..100 且分布合理（多次抽样覆盖）；`get_sign`/`all_signs` 完整性（恰 100 条、字段非空、grade 在允许集合内）；`QianOracle` 组 prompt 含签诗+吉凶+问题+人设（fake client）；`/qian/oracle/stream` 端点（fake client + monkeypatch）吐 sign+text+camera+done、持久化 QianReading。复用 ziwei 流式测试套路。
- 前端：tsc + CI build + 浏览器/prod 肉眼（无单测框架，遵循既有模式）；3D 与配色观感由用户确认。

## 13. V1 / 扩展边界

- **V1**：观音 100 签 + 极简仪式 + 独立板块 + 解签人单人设 + 流式&配音 + 历史。
- **扩展**：关帝/月老/黄大仙/诸葛等多套签（语料可插拔）；掷筊杯确认仪式；摇手机/拖拽交互；签筒物理感增强；`/ziwei/tts` 中性化为 `/tts`。

## 14. 部署

按 [[deployment_rules]]：commit → push main → tag → GitHub Actions。前端无单测，CI `next build` + 后端 pytest 为门槛；上线后 prod 实测（抽签分布、解签流式、配音、3D 观感）。
