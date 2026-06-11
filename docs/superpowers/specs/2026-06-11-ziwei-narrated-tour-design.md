# 紫微解盘 · 叙事化播放（声音解说 + 慢镜头编排 + 结束脚本）设计

日期：2026-06-11
状态：已和用户敲定，待写实现计划
所属：紫微斗数 3D 算命板块 Phase 3d（在 main 直接做，无独立 worktree）

## 1. 背景与动机

v0.37.0 已上线真·SSE 流式解盘：文字逐字流、镜头随标记即时触发，感知首字 ~3.9s。

用户反馈：**镜头转得太快人眼跟不上；既要看文字又要看 3D 画面，用户体验不佳。** 期望：镜头慢慢转场、配上**声音解说**、文字作为**结束后的脚本**呈现。

这是一次播放层的**范式转变**：从「尽快把字打完」转为「以**声音为主时钟**的叙事化导览」——镜头缓慢飞向一宫并停驻、声音讲解该宫、讲完再飞下一宫；解读期间屏上几乎不显正文，整篇文字在结束后作为脚本落入对话坞供阅读/回看。

后端流式端点不浪费：它正是「即时编排」的理想数据源（见 §4）。

## 2. 目标 / 非目标

**目标（V1，纯前端）**
- 声音解说（V1 用浏览器内置语音，**默认出声**）。
- 慢镜头编排：一宫一拍，镜头先慢飞、停驻，声音后到。
- 解读期屏上几乎不显正文（仅极简提示 + 术语卡）；结束后整篇脚本入对话坞。
- 静音开关、跳过键、reduced-motion 与语音不可用的降级。
- 历史消息可「重新解读」（用已存 segments 重演，不调 AI）。
- 声音源做成**可替换接口**，为 V2 云端 TTS 留好位。

**非目标**
- V1 不做云端 TTS / 后端 `/tts` 端点（留 V2）。
- 不做逐字卡拉OK字幕（已决定解读期几乎不显字）。
- 不改后端（V1 后端零改动）。
- 不做 Phase 4 记忆蒸馏（独立阶段）。

## 3. 体验流程

1. 用户输入问题 → 点「问」。该点击同时解锁浏览器语音权限（autoplay 策略要求用户手势）。
2. 「凝神观盘…」过渡（~4s，等第一拍就绪），3D 场景维持轻微自转，避免画面僵死。
3. **编排化解读**，逐拍进行。每拍：
   - 镜头**慢慢**飞向该宫（smoothTime ≈ 1.5s）并停驻；`overview` 则缓拉回总览；`explain_term` 浮出术语卡。
   - 声音解说**本拍文字**（await 朗读结束）。
   - 进入下一拍。
   - 屏上仅一行极简提示（如「解盘师正在解读 · 命宫」）+ 🔇 静音 + 「直接看文字」跳过。
4. 全部讲完 → 镜头缓缓回总览 → **整篇文字脚本**填入对话坞助手气泡，存入历史。

**首次进页面**：一次性轻提示「🔊 解读将有声，可随时静音」（localStorage 记忆，不再重复）。

## 4. 架构：流式喂给「指挥器」

```
streamOracle ──(text 增量 / camera 边界 / done)──► 节拍队列 ──► useOracleTour 指挥器
                                                                  每拍：
                                                                  ├─ fireCamera(慢) → onFocusBranch / onTerm
                                                                  ├─ await narration.speak(本拍文字)
                                                                  └─ 下一拍
                                                  done 且队列排空 ──► 揭晓全文脚本 + 回总览
```

### 4.1 节拍的定义

**一拍 =（前导文字 + 紧随其后的镜头指令）。** 这正是 `StreamMarkerParser` 在每个 `[[focus]]/[[overview]]/[[term]]` 边界已经产出的结构：文字描述某宫，末尾跟该宫的镜头标记。

- `onText(delta)`：累积到当前拍的文字缓冲。
- `onCamera(cmd)`：把「已累积文字 + 本镜头」**入队**为一拍，清空缓冲。
- `onDone`：若缓冲尚有残余文字（末尾无镜头的收尾段），作为**最后一拍（无镜头）**入队；并标记流结束。

### 4.2 镜头先动、解说后到

每拍**先 fireCamera 再 narrate**（与旧回放「先打字后飞镜头」相反）。因为标记紧跟在描述该宫的句子之后，所以「先飞向命宫，再朗读这段讲命宫的话」在叙事上完全顺：镜头漂向命宫的同时，声音开始讲命宫。镜头有整段朗读的时长可以从容漂移并停驻——这就是「慢慢转场」。

### 4.3 生产者 / 消费者

流处理器（生产者）只管入队；指挥器（消费者）异步循环只管出队表演，每拍 `await narration.speak(text)`。因为「生成」远快于「朗读」，首拍（~4s）之后队列基本不饿；若偶尔出队追上生产（队空但流未结束），消费者等待下一次入队信号。

队列实现：一个简单的 async 队列——`items: Beat[]`、`done: boolean`、一个 `notify` 唤醒机制（resolve 一个 pending 的 waiter）。消费循环：

```
while (true):
  if items 非空: beat = items.shift(); 表演(beat)
  else if done: break
  else: await 下一次 notify（新入队或 done）
```

## 5. 可替换声音源

```ts
// lib/ziwei/narration.ts
export interface NarrationSource {
  speak(text: string): Promise<void>; // 朗读完成（或定时结束）时 resolve；被 cancel 时也 resolve/reject 统一处理
  cancel(): void;                      // 立即停止当前朗读
}
```

- **`BrowserNarration`（V1 默认）**：`window.speechSynthesis` + `SpeechSynthesisUtterance`。
  - 挑选 `zh-CN`/`zh` 嗓音（`getVoices()`，可能异步，需等 `voiceschanged`）。
  - `rate ≈ 0.92`（略慢，解盘调性），`pitch` 默认。
  - `utterance.onend` → resolve；`onerror` → resolve（不卡死，降级为静默继续）。
  - `cancel()` → `speechSynthesis.cancel()`。
  - 空文本（纯镜头拍）直接 resolve（仍给一个短停驻 beat，见 §6）。
- **`SilentNarration`**：静音 / 语音不支持 / 出错时使用。`speak(text)` = `setTimeout(resolve, estimateDuration(text))`。
  - `estimateDuration(text) = clamp(text.length × 180ms, 最小 800ms, 最大 12000ms)`（纯镜头空拍给一个固定 ~900ms 停驻）。
  - `cancel()` 清除定时器并 resolve。
- **`estimateDuration`**：导出供测试与 SilentNarration 共用。
- **V2**：新增 `CloudNarration`（拉后端 `/tts` 返回的音频片段，`HTMLAudioElement` 播放，`onended` resolve）。指挥器与前端 UI **零改动**，只换注入的 NarrationSource。

**选择逻辑**：默认出声 → `BrowserNarration`（若 `speechSynthesis` 存在且能拿到中文嗓音）；用户点静音 / 不支持 / reduced-motion 仅朗读关 → `SilentNarration`。运行中切静音：cancel 当前并把后续拍换成 SilentNarration。

## 6. 指挥器 `useOracleTour`

输入：`segments 流`（经由 streamOracle 的 handlers 入队）、`deps = { chart, onFocusBranch, onTerm, setCaption, getNarration, onScriptReveal, setTourActive }`。

每拍表演：
1. `setCaption(本拍宫名或「解读中」)`（极简提示）。
2. 若有镜头：`fireCamera(cmd, {chart, onFocusBranch, onTerm})`（focus→慢飞 / overview→慢拉回 / term→术语卡）。
3. **settle beat**：等一个短暂 ~500ms 让镜头起步（镜头在朗读期间继续漂移到位）。
4. `await getNarration().speak(beat.text)`（空文本拍给 ~900ms 停驻而非朗读）。
5. 拍间小停 ~300ms。

收尾（流 done 且队列排空）：`onScriptReveal(全文)`（把助手气泡内容设为整篇 clean 文本）、`onFocusBranch(null)` 缓回总览、`setCaption(null)`、`setTourActive(false)`、关闭术语卡。

指挥器维护一个 **fullText 累加器**（所有已入队拍的 text 顺序拼接），揭晓脚本时用它。

**控制**：
- `cancel()`：停消费循环 + `narration.cancel()` + **abort 流** + 不揭晓（用于切档案/重新提问，外层会重置整个对话区）。这是唯一会 abort 流的路径。
- `skip()`：停声音+镜头（`narration.cancel()`、消费循环不再表演），但**不 abort 流**——让流在后台跑完以保证后端持久化与 conversation_id 落定。切到「直出」模式：后续 `onText` 直接追加到 assistant 气泡、`onDone` 揭晓最终全文并落 conv_id。立即把已累积 fullText 揭晓 + 缓回总览。
  - 理由：skip 是「我现在就想读字」，不是「取消这次解读」——读数仍应入库。abort 会让后端生成器收到客户端断开而可能不持久化（仅 `cancel()` 那种真正放弃的场景才 abort）。
- 全程不泄漏定时器 / utterance（cancel 清理）。

## 7. 慢镜头

`CameraRig` 增加 `smoothTime?: number` prop（默认 0.45 保持手动拖拽跟手）。`CameraControls` 的 `smoothTime` 控制 `setLookAt(…, transition=true)` 的过渡时长。

- 解读期：`ZiweiWorkspace` 持有 `tourActive` 状态，下传到 `ChartView → CameraRig`，`tourActive ? 1.5 : 0.45`。
- 解读结束恢复 0.45，手动拖拽不受影响。

## 8. chat-dock 改造

`handleSend`：
1. 起 `AbortController`；插入 user 气泡 + 空 assistant 气泡（`pending`）。
2. `setTourActive(true)`；选定 NarrationSource（默认 BrowserNarration）。
3. 调 `streamOracle(profileId, body, handlers, signal)`，handlers 把 text/camera/done 喂进 `useOracleTour` 的队列（**不再逐字铺到气泡**——解读期气泡只显极简提示）。
4. 指挥器逐拍表演；`onScriptReveal` 时把 assistant 气泡内容设为全文、`pending=false`、`setConversationId(done.conversation_id)`、`setTourActive(false)`。
5. 错误：`onError`（后端 salvage）→ 揭晓已得文本（若有）否则提示失败；catch 校验错误（404/429/503）→ 移除空气泡 + 本地化提示（沿用现有）。

**解读态 UI**（assistant 气泡在 pending 期间）：一行脉冲提示「✦ 解盘师正在解读 · {caption}」+ 🔇 静音切换 + 「直接看文字」按钮。结束后气泡变为正常全文脚本。

**历史消息**：每条 assistant 消息（有 segments）显示一个「▶ 重新解读」小按钮 → 用该消息已存的 segments 直接喂指挥器重演（不调 AI、不入库、零成本）。重演用一个「合成流」：把 segments 依次按 §4.1 规则即时入队 + 立即 done。

## 9. 降级与边界

| 情况 | 行为 |
|---|---|
| reduced-motion | 不做飞行编排：等价于一开页即「直出」模式——`onText` 直接逐增量铺进气泡（同旧流式观感）、不动镜头、`onDone` 落 conv_id。默认仍朗读整段（可静音） |
| `speechSynthesis` 不可用 / 拿不到中文嗓音 | 自动用 SilentNarration（按估时定拍），体验不中断 |
| 朗读 onerror | 该拍降级为静默 resolve，继续后续拍 |
| autoplay 被拦 | 因「问」是用户手势，正常可出声；万一失败则静默继续 |
| 切档案 / 重新提问 | abort 流 + narration.cancel + tour.cancel + 重置（沿用 prevId 渲染期重置 + in-flight profileId 守卫） |
| 流中途 error | 同 §8.5，揭晓 salvage 文本 |

## 10. 组件与文件

| 文件 | 改动 | 职责 |
|---|---|---|
| `lib/ziwei/narration.ts` | 新增 | NarrationSource 接口 + BrowserNarration + SilentNarration + estimateDuration |
| `components/ziwei/chat-dock/use-oracle-tour.ts` | 新增 | 指挥器：节拍队列 + 逐拍表演 + cancel/skip/mute + 合成流（历史重演） |
| `components/ziwei/scene3d/camera-rig.tsx` | 改 | 加 `smoothTime` prop |
| `components/ziwei/chat-dock/chat-dock.tsx` | 改 | handleSend 走指挥器；解读态 UI（提示行 + 🔇 + 跳过）；历史「▶ 重新解读」 |
| `components/ziwei/ziwei-workspace.tsx` | 改 | 持有/下传 `tourActive` |
| `components/ziwei/chat-dock/camera.ts` | 复用 | fireCamera |
| `lib/ziwei/api.ts` | 复用 | streamOracle |

后端：**V1 零改动**。

## 11. 测试

- `estimateDuration`：边界（空串、超长、clamp）。
- 节拍分拍逻辑：给定 (text 增量序列, camera 事件, done) → 断言正确的拍序（拍数、每拍 text、每拍 command；末尾无镜头残余成最后一拍；连续同镜头去重已在解析层处理）。
- 指挥器：用 **fake NarrationSource**（speak 立即 resolve、记录调用顺序）断言「每拍先 fireCamera 后 speak」、cancel/skip 不再继续、结束揭晓全文。
- 合成流（历史重演）：segments → 正确拍序 + 立即 done。
- 浏览器真实听感 / 慢镜头观感由用户在 prod 肉眼肉耳确认（前端逻辑已测 + tsc/build 干净）。

## 12. V1 / V2 边界

- **V1（本轮）**：浏览器语音（默认出声）+ 流式喂的慢编排 + 静音/跳过/降级 + 结束全文脚本 + 历史重演。纯前端，后端零改。
- **V2（以后）**：后端 `/tts` 端点（云 TTS，温暖中文「解盘师」嗓音）+ `CloudNarration`。接口已留好，指挥器/UI 不动。

## 13. 部署

按 [[deployment_rules]]：commit → push main → tag（预计 v0.38.0）→ GitHub Actions。完成后 prod 实测首次解说延迟（预期 ~4s）+ 用户肉眼/耳确认观感。
