# 紫微斗数 Phase 2（3D 主体验）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 /ziwei 的 2D 方盘升级为悬浮在星空中的 3D 玄殿罗盘——可拖转俯瞰、星曜为发光光球、四化为飞渡光束、点宫位一镜到底飞入星曜环形殿牌内景；2D 盘保留为 WebGL 不可用时的兜底并提供手动切换。

**Architecture:** R3F Canvas 经 `dynamic(ssr:false)` 隔离在 `/ziwei` 路由的客户端组件里；三层场景（环境星空 / 玄殿方盘 / 单宫内景）+ CameraControls 运镜；中文 3D 文字用构建期生成的 Noto Sans SC 子集字体（woff，troika 不支持 woff2）+ drei `<Text>` 的 `font`+`characters` 预载；PerformanceMonitor 自动降档（dpr/Bloom/粒子），尊重 prefers-reduced-motion。

**Tech Stack（版本已对 npm registry 核实，2026-06-10）:** three@0.184.0、@types/three@0.184.1、@react-three/fiber@9.6.1（peer react >=19 <19.3 ✓）、@react-three/drei@10.7.7（peer fiber ^9、three >=0.159 ✓）、@react-three/postprocessing@3.0.4、subset-font@2.5.0（仅构建期）、Noto Sans SC（OFL-1.1，源自 googlefonts/noto-cjk）。

**Spec:** `docs/superpowers/specs/2026-06-09-ziwei-3d-design.md`（§3 视觉与交互、§9 降级、§11 分期第 2 条）

**Phase 1 既有约束（勿违反）：**
- `ZiweiChart` JSON 结构（`frontend/src/lib/ziwei/types.ts`）是渲染唯一数据源，不改。
- 2D 盘 `ChartGrid2D` 不删——它是 WebGL 兜底（spec §9）。
- 删除按钮等模式照 Phase 1 评审结论（交互元素不嵌套在 button 里）。
- 前端无测试框架：每任务用 `npx tsc --noEmit` + `npm run build` + 浏览器实测验证；不要引入测试框架。
- Windows PowerShell 环境（`;` 链接命令，无 `&&`）；worktree 分支 `worktree-ziwei-phase2`，只 commit 不 push。

**drei/troika API 注意：** 计划中的 drei 组件 props 以 `node_modules` 实际 `.d.ts` 为准；如有出入按真实类型修正，**不许用 `any` 糊**，并在汇报中注明改了什么。

---

## 场景设计总览（各任务共享的坐标与状态约定）

**坐标系：** 方盘躺在 XZ 平面（Y 朝上）。格子宽 `CELL_W=2.6`（x 方向）、深 `CELL_D=3.4`（z 方向）。沿用 2D 的地支→(row,col) 映射（row 1-4 自上而下 → z 由负到正；col 1-4 自左而右 → x 由负到正）：

```
position(col, row) = [ (col - 2.5) * CELL_W, 0, (row - 2.5) * CELL_D ]
```

中宫占 (2,2)-(3,3)，即位于原点，尺寸约 (2*CELL_W-0.3) × (2*CELL_D-0.3)。

**相机：** 默认总览 `position≈(0, 12, 10.5)` 看向原点（俯角约 50°，与 2D 视觉延续）。飞入单宫：look-at 目标=宫位中心，相机=宫位中心 + (0, 3.2, 2.6)。

**选宫状态：** `selectedBranch: string | null`（地支字符串）由 `ChartView` 持有，传给 3D 场景；Phase 3 的 AI 镜头指令将复用同一状态入口。

**性能档位：** `quality: "high" | "low"`。low = dpr 1、关 Bloom、Sparkles 减半、星点数减半。PerformanceMonitor onDecline 自动降档，不自动升回（避免抖动）。

**动效原则（UX-first）：** 所有运镜可被用户操作打断；`prefers-reduced-motion: reduce` 时入场动画跳过、相机切换瞬时完成。

---

### Task 1: 依赖安装 + 中文字体子集工具链

**Files:**
- Modify: `frontend/package.json`（新依赖）
- Create: `frontend/scripts/build-ziwei-font.cjs`（子集生成脚本，开发期工具）
- Create: `frontend/public/fonts/ziwei-3d.woff`（脚本生成后提交）
- Create: `frontend/src/components/ziwei/scene3d/glyphs.ts`（脚本生成：字形集常量）
- Create: `frontend/public/fonts/LICENSE-NotoSansSC.txt`（OFL 协议文本，履行许可义务）

- [ ] **Step 1: 安装依赖**

Run: `cd frontend; npm install three@0.184.0 @react-three/fiber@9.6.1 @react-three/drei@10.7.7 @react-three/postprocessing@3.0.4; npm install -D @types/three@0.184.1 subset-font@2.5.0`
Expected: package.json 出现上述 6 个依赖（注意 npm cafile 已配置 Norton 证书，安装应正常）

- [ ] **Step 2: 写字体子集脚本**

创建 `frontend/scripts/build-ziwei-font.cjs`：

```javascript
/**
 * 生成 3D 场景用的中文字体子集（troika-three-text 不支持 woff2，输出 woff）。
 * 字形来源：精选常量（覆盖星曜/宫位/干支/亮度/四化/农历/UI）∪ iztro zh-CN локale 能找到的字符串。
 * 产物：public/fonts/ziwei-3d.woff + src/components/ziwei/scene3d/glyphs.ts
 * 用法：node scripts/build-ziwei-font.cjs [本地NotoSansSC路径]
 *      不传路径时自动从 googlefonts/noto-cjk 下载 NotoSansSC-Regular.otf（约16MB，仅本次运行用，不入库）。
 */
const fs = require("fs");
const path = require("path");
const os = require("os");
const subsetFont = require("subset-font");

const FONT_URL =
  "https://raw.githubusercontent.com/googlefonts/noto-cjk/main/Sans/SubsetOTF/SC/NotoSansSC-Regular.otf";
const OUT_FONT = path.join(__dirname, "..", "public", "fonts", "ziwei-3d.woff");
const OUT_GLYPHS = path.join(__dirname, "..", "src", "components", "ziwei", "scene3d", "glyphs.ts");

// —— 精选字形（即使 iztro locale 抓取失败也足够渲染）——
const CURATED = [
  // 十四主星 + 常见辅佐煞曜
  "紫微天机太阳武曲同廉贞府阴贪狼巨门相梁七杀破军",
  "文昌曲左辅右弼魁钺禄存马擎羊陀罗火星铃地空劫解神台辅封诰恩光贵咸池华盖红鸾喜孤辰寡宿蜚廉年",
  "三八座龙池凤阁截路旬中伤使月德巫刑姚宫符",
  // 十二宫名
  "命兄弟夫妻子女财帛疾厄迁移交友仆役官禄田宅福德父母身",
  // 干支
  "甲乙丙丁戊己庚辛壬癸子丑寅卯辰巳午未申酉戌亥",
  // 亮度 / 四化 / 五行局
  "庙旺得利平不陷",
  "权科忌",
  "水二局木金四土五火六",
  // 农历与日期
  "〇一二三四五六七八九十百千廿卅初正腊冬闰年月日时分早晚",
  // 生肖 + 星座
  "鼠牛虎兔蛇羊猴鸡狗猪白羊金牛双鱼巨蟹狮处女秤天蝎射手摩羯瓶座",
  // 3D UI 文案
  "返回总览点击进入宫位详情运限大限流飞入退出加载中切换视角长生沐浴冠带临帝衰病死墓绝胎养",
  // 中宫/殿牌字面标签（Task 4/6 JSX 模板用字，缺失会渲染成隐形文字）
  "公历农主化—",
  // ASCII（数字/标点/英文字母小写大写常用符号）
  "0123456789 ·.-~:()（）/",
  "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
].join("");

function collectFromIztro() {
  const chars = new Set();
  const visit = (node) => {
    if (typeof node === "string") for (const ch of node) chars.add(ch);
    else if (Array.isArray(node)) node.forEach(visit);
    else if (node && typeof node === "object") Object.values(node).forEach(visit);
  };
  try {
    // iztro 的 zh-CN 资源（路径以实际包结构为准；失败则仅用精选集）
    // eslint-disable-next-line global-require
    visit(require("iztro/lib/i18n/locales/zh-CN"));
    console.log(`iztro zh-CN locale 抓取成功，新增 ${chars.size} 个候选字符`);
  } catch (e) {
    console.warn("未能加载 iztro locale（不影响产出，使用精选字形集）:", e.message);
  }
  return chars;
}

async function getSourceFont() {
  const localPath = process.argv[2];
  if (localPath) return fs.readFileSync(localPath);
  const tmp = path.join(os.tmpdir(), "NotoSansSC-Regular.otf");
  if (fs.existsSync(tmp)) {
    console.log("使用缓存的源字体:", tmp);
    return fs.readFileSync(tmp);
  }
  console.log("下载 Noto Sans SC（约16MB，仅本次使用）……");
  const res = await fetch(FONT_URL);
  if (!res.ok) throw new Error(`下载失败 ${res.status}：可手动下载后执行 node scripts/build-ziwei-font.cjs <路径>`);
  const buf = Buffer.from(await res.arrayBuffer());
  fs.writeFileSync(tmp, buf);
  return buf;
}

(async () => {
  const glyphSet = new Set(CURATED);
  for (const ch of collectFromIztro()) glyphSet.add(ch);
  const text = [...glyphSet].sort().join("");

  const source = await getSourceFont();
  const woff = await subsetFont(source, text, { targetFormat: "woff" });
  if (woff.length > 400 * 1024) throw new Error("子集异常偏大（>400KB），检查字形集是否混入大量无关字符");

  fs.mkdirSync(path.dirname(OUT_FONT), { recursive: true });
  fs.writeFileSync(OUT_FONT, woff);

  fs.mkdirSync(path.dirname(OUT_GLYPHS), { recursive: true });
  fs.writeFileSync(
    OUT_GLYPHS,
    `// 由 scripts/build-ziwei-font.cjs 生成，勿手改；重新生成后一并提交字体文件\n` +
      `/** 3D 场景字体路径（troika 仅支持 ttf/otf/woff） */\n` +
      `export const ZIWEI_FONT_URL = "/fonts/ziwei-3d.woff";\n` +
      `/** 子集包含的全部字形——传给 drei <Text characters> 预生成 SDF */\n` +
      `export const ZIWEI_GLYPHS =\n  ${JSON.stringify(text)};\n`,
  );

  console.log(`OK: ${glyphSet.size} 字形 → ${OUT_FONT}（${(woff.length / 1024).toFixed(1)} KB）`);
})().catch((e) => {
  console.error(e.message);
  process.exit(1);
});
```

- [ ] **Step 3: 运行脚本生成字体**

Run: `cd frontend; node scripts/build-ziwei-font.cjs`
Expected: 打印 `OK: <N> 字形 → ...ziwei-3d.woff（<size> KB）`，size 在 60–400KB 之间；`public/fonts/ziwei-3d.woff` 与 `src/components/ziwei/scene3d/glyphs.ts` 生成

- [ ] **Step 4: 放置 OFL 许可文本**

创建 `frontend/public/fonts/LICENSE-NotoSansSC.txt`，内容为一行说明 + 指引：

```
ziwei-3d.woff is a subset of Noto Sans SC (c) Google,
licensed under the SIL Open Font License 1.1.
Full license: https://github.com/googlefonts/noto-cjk/blob/main/Sans/LICENSE
Generated by frontend/scripts/build-ziwei-font.cjs
```

- [ ] **Step 5: 类型检查 + Commit**

Run: `cd frontend; npx tsc --noEmit`
Expected: 无错误

```bash
git add frontend/package.json frontend/package-lock.json frontend/scripts/build-ziwei-font.cjs frontend/public/fonts/ frontend/src/components/ziwei/scene3d/glyphs.ts
git commit -m "feat(ziwei): R3F deps and CJK subset font toolchain for 3D text"
```

---

### Task 2: ChartView 容器——WebGL 检测、2D/3D 切换、动态加载

**Files:**
- Create: `frontend/src/components/ziwei/chart-view.tsx`
- Create: `frontend/src/components/ziwei/scene3d/scene-3d.tsx`（本任务先是最小可渲染场景，后续任务充实）
- Modify: `frontend/src/app/ziwei/page.tsx`（`ChartGrid2D` → `ChartView`）

- [ ] **Step 1: 写最小 3D 场景**

创建 `frontend/src/components/ziwei/scene3d/scene-3d.tsx`：

```tsx
"use client";

import { Suspense } from "react";
import { Canvas } from "@react-three/fiber";
import { Text } from "@react-three/drei";
import type { ZiweiChart } from "@/lib/ziwei/types";
import { ZIWEI_FONT_URL, ZIWEI_GLYPHS } from "./glyphs";

export type Scene3DProps = {
  chart: ZiweiChart;
  selectedBranch: string | null;
  onSelectBranch: (branch: string | null) => void;
};

/** 最小场景：验证 Canvas + 中文字体管线。后续任务在此基础上展开三层场景。 */
export default function Scene3D({ chart }: Scene3DProps) {
  return (
    <Canvas dpr={[1, 1.75]} camera={{ position: [0, 12, 10.5], fov: 42 }} style={{ background: "#050310" }}>
      <Suspense fallback={null}>
        <Text font={ZIWEI_FONT_URL} characters={ZIWEI_GLYPHS} fontSize={1} color="#d8c8ff" position={[0, 0, 0]}>
          {chart.fiveElementsClass}
        </Text>
      </Suspense>
    </Canvas>
  );
}
```

- [ ] **Step 2: 写 ChartView 容器**

创建 `frontend/src/components/ziwei/chart-view.tsx`：

```tsx
"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { ChartGrid2D } from "@/components/ziwei/chart-grid-2d";
import type { ZiweiChart } from "@/lib/ziwei/types";

const Scene3D = dynamic(() => import("./scene3d/scene-3d"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full min-h-[480px] items-center justify-center">
      <p className="animate-pulse text-sm text-violet-300/60">正在汇聚星辰……</p>
    </div>
  ),
});

const VIEW_KEY = "ziwei-view-mode";

function detectWebGL(): boolean {
  // 每次探测用全新 canvas：getContext("webgl2") 失败也会锁定该 canvas 的 context 模式，
  // 复用同一个 canvas 会让后续 "webgl" 探测恒为 null（老设备被误判为不支持）
  const probe = (type: "webgl2" | "webgl") => {
    try {
      return Boolean(document.createElement("canvas").getContext(type));
    } catch {
      return false;
    }
  };
  return probe("webgl2") || probe("webgl");
}

export function ChartView({ chart }: { chart: ZiweiChart }) {
  // null = 检测中（SSR 安全：首帧渲染 2D，挂载后决定）
  const [webgl, setWebgl] = useState<boolean | null>(null);
  const [mode, setMode] = useState<"3d" | "2d">("3d");
  const [selectedBranch, setSelectedBranch] = useState<string | null>(null);

  // 档案切换时重置选宫（不能用 key 重挂——那会销毁 WebGL 上下文重跑检测）
  const [prevChart, setPrevChart] = useState(chart);
  if (prevChart !== chart) {
    setPrevChart(chart);
    setSelectedBranch(null);
  }

  // useLayoutEffect：在首帧绘制前定下 webgl/mode，避免 2D 盘闪现一帧再切 3D
  useLayoutEffect(() => {
    setWebgl(detectWebGL());
    try {
      const saved = window.localStorage.getItem(VIEW_KEY);
      if (saved === "2d" || saved === "3d") setMode(saved);
    } catch {
      // 隐私模式下 localStorage 可能直接 throw——持久化本就尽力而为
    }
  }, []);

  const switchMode = (next: "3d" | "2d") => {
    setMode(next);
    setSelectedBranch(null); // 模式往返不保留选宫（约定：3D→2D→3D 回到总览）
    try {
      window.localStorage.setItem(VIEW_KEY, next);
    } catch {
      // 同上
    }
  };

  const show3d = mode === "3d" && webgl === true;

  return (
    <div className="relative overflow-hidden rounded-[28px] border border-violet-500/20 bg-[#050310] shadow-[0_20px_50px_rgba(91,33,182,0.25)]">
      {/* 模式切换（WebGL 不可用时隐藏 3D 选项） */}
      {webgl !== false ? (
        <div className="absolute right-3 top-3 z-10 flex gap-1 rounded-full border border-violet-500/30 bg-[#120a2e]/80 p-1 backdrop-blur">
          {(["3d", "2d"] as const).map((m) => (
            <button
              key={m}
              type="button"
              aria-pressed={mode === m}
              onClick={() => switchMode(m)}
              className={`rounded-full px-3 py-1 text-xs font-semibold transition-colors ${
                mode === m ? "bg-violet-600 text-white" : "text-violet-300/70 hover:text-violet-100"
              }`}
            >
              {m === "3d" ? "3D 星盘" : "2D 方盘"}
            </button>
          ))}
        </div>
      ) : null}

      {show3d ? (
        <div className="h-[72vh] min-h-[480px]">
          <Scene3D chart={chart} selectedBranch={selectedBranch} onSelectBranch={setSelectedBranch} />
        </div>
      ) : (
        <div className="p-2 sm:p-3">
          {webgl === false ? (
            <p className="px-2 pb-2 text-xs text-violet-300/60">当前设备不支持 WebGL，已切换为 2D 命盘。</p>
          ) : null}
          <ChartGrid2D chart={chart} />
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: 接入页面**

修改 `frontend/src/app/ziwei/page.tsx`：

1. 把 `import { ChartGrid2D } from "@/components/ziwei/chart-grid-2d";` 替换为 `import { ChartView } from "@/components/ziwei/chart-view";`
2. 把 `<ChartGrid2D chart={chart} />` 替换为 `<ChartView chart={chart} />`

其余不动（2D 组件自身的外框样式与 ChartView 外框略有重复——属预期，ChartGrid2D 仍被独立使用语义保留）。

- [ ] **Step 4: 验证**

Run: `cd frontend; npx tsc --noEmit; npm run build`
Expected: 无错误；`/ziwei` 路由仍在 build 输出中

浏览器验证（dev server + 已有档案）：/ziwei 默认显示 3D 容器，中央渲染出中文「木三局」（证明字体子集管线通了）；右上角切到「2D 方盘」显示原 2D 盘并在刷新后记住选择。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ziwei/chart-view.tsx frontend/src/components/ziwei/scene3d/scene-3d.tsx frontend/src/app/ziwei/page.tsx
git commit -m "feat(ziwei): ChartView container with WebGL detection, 3D/2D toggle, dynamic Canvas"
```

---

### Task 3: 环境层——星空、星云、后期辉光、性能档位

**Files:**
- Create: `frontend/src/components/ziwei/scene3d/starfield.tsx`
- Create: `frontend/src/components/ziwei/scene3d/effects.tsx`
- Modify: `frontend/src/components/ziwei/scene3d/scene-3d.tsx`（充实为正式 shell）

- [ ] **Step 1: 星空环境组件**

创建 `frontend/src/components/ziwei/scene3d/starfield.tsx`：

```tsx
"use client";

import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Sparkles, Stars } from "@react-three/drei";
import * as THREE from "three";

/** 用 canvas 画一张径向渐变贴图作星云 sprite（免外部资源） */
function makeNebulaTexture(inner: string, outer: string): THREE.CanvasTexture {
  const size = 256;
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext("2d")!;
  const grad = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  grad.addColorStop(0, inner);
  grad.addColorStop(1, outer);
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, size, size);
  const texture = new THREE.CanvasTexture(canvas);
  texture.needsUpdate = true;
  return texture;
}

function Nebula({ position, scale, inner }: { position: [number, number, number]; scale: number; inner: string }) {
  const texture = useMemo(() => makeNebulaTexture(inner, "rgba(5,3,16,0)"), [inner]);
  const ref = useRef<THREE.Sprite>(null);
  useFrame(({ clock }) => {
    if (!ref.current) return;
    const t = clock.getElapsedTime();
    ref.current.position.x = position[0] + Math.sin(t * 0.05) * 1.2;
    ref.current.position.y = position[1] + Math.cos(t * 0.04) * 0.8;
  });
  return (
    <sprite ref={ref} position={position} scale={[scale, scale, 1]}>
      <spriteMaterial map={texture} transparent opacity={0.5} depthWrite={false} />
    </sprite>
  );
}

export function Starfield({ quality }: { quality: "high" | "low" }) {
  const starCount = quality === "high" ? 4500 : 2200;
  const sparkleCount = quality === "high" ? 90 : 40;
  return (
    <group>
      <Stars radius={60} depth={40} count={starCount} factor={3.2} saturation={0.4} fade speed={0.6} />
      <Sparkles count={sparkleCount} scale={[34, 18, 34]} size={2.4} speed={0.25} opacity={0.55} color="#c4b5fd" />
      <Nebula position={[-14, 6, -18]} scale={34} inner="rgba(124,58,237,0.32)" />
      <Nebula position={[16, 9, -22]} scale={40} inner="rgba(56,120,220,0.22)" />
      <Nebula position={[2, -7, -16]} scale={26} inner="rgba(190,80,200,0.16)" />
    </group>
  );
}
```

- [ ] **Step 2: 后期效果组件**

创建 `frontend/src/components/ziwei/scene3d/effects.tsx`：

```tsx
"use client";

import { Bloom, EffectComposer, Vignette } from "@react-three/postprocessing";

/** 低档位直接不渲染 Composer（省一条渲染管线） */
export function SceneEffects({ quality }: { quality: "high" | "low" }) {
  if (quality === "low") return null;
  return (
    <EffectComposer>
      <Bloom luminanceThreshold={0.35} luminanceSmoothing={0.85} intensity={0.9} mipmapBlur />
      <Vignette eskil={false} offset={0.18} darkness={0.85} />
    </EffectComposer>
  );
}
```

- [ ] **Step 3: 充实场景 shell**

重写 `frontend/src/components/ziwei/scene3d/scene-3d.tsx`：

```tsx
"use client";

import { Suspense, useState } from "react";
import { Canvas } from "@react-three/fiber";
import { CameraControls, PerformanceMonitor, Text } from "@react-three/drei";
import type { ZiweiChart } from "@/lib/ziwei/types";
import { Starfield } from "./starfield";
import { SceneEffects } from "./effects";
import { ZIWEI_FONT_URL, ZIWEI_GLYPHS } from "./glyphs";

export type Scene3DProps = {
  chart: ZiweiChart;
  selectedBranch: string | null;
  onSelectBranch: (branch: string | null) => void;
};

export default function Scene3D({ chart }: Scene3DProps) {
  const [quality, setQuality] = useState<"high" | "low">("high");

  return (
    <Canvas
      dpr={quality === "high" ? [1, 1.75] : 1}
      camera={{ position: [0, 12, 10.5], fov: 42 }}
      style={{ background: "#050310" }}
    >
      <PerformanceMonitor onDecline={() => setQuality("low")}>
        <color attach="background" args={["#050310"]} />
        <fog attach="fog" args={["#050310", 26, 60]} />
        <ambientLight intensity={0.55} />
        <directionalLight position={[6, 14, 8]} intensity={0.7} color="#cdb8ff" />

        <Suspense fallback={null}>
          <Starfield quality={quality} />
          {/* 占位：Task 4 替换为 <MysticBoard /> */}
          <Text font={ZIWEI_FONT_URL} characters={ZIWEI_GLYPHS} fontSize={1} color="#d8c8ff" position={[0, 0.5, 0]}>
            {chart.fiveElementsClass}
          </Text>
          <SceneEffects quality={quality} />
        </Suspense>

        <CameraControls makeDefault minDistance={6} maxDistance={28} maxPolarAngle={Math.PI * 0.46} />
      </PerformanceMonitor>
    </Canvas>
  );
}
```

- [ ] **Step 4: 验证**

Run: `cd frontend; npx tsc --noEmit; npm run build` — 无错误。
浏览器：星空 + 三团星云缓慢漂移 + 中央发光文字（Bloom 生效）；可拖转/缩放，俯角被限制不会钻到盘下面。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ziwei/scene3d/
git commit -m "feat(ziwei): starfield environment, bloom postprocessing, performance tiers"
```

---

### Task 4: 玄殿方盘——宫位殿板与中宫

**Files:**
- Create: `frontend/src/components/ziwei/scene3d/layout.ts`
- Create: `frontend/src/components/ziwei/scene3d/palace-plate.tsx`
- Create: `frontend/src/components/ziwei/scene3d/mystic-board.tsx`
- Modify: `frontend/src/components/ziwei/scene3d/scene-3d.tsx`（占位文字 → `<MysticBoard />`）

- [ ] **Step 1: 布局常量**

创建 `frontend/src/components/ziwei/scene3d/layout.ts`：

```typescript
/** 3D 方盘布局：沿用 2D 的地支固定位（chart-grid-2d.tsx BRANCH_GRID），映射到 XZ 平面 */

export const CELL_W = 2.6;
export const CELL_D = 3.4;
export const PLATE_H = 0.18;

export const BRANCH_GRID: Record<string, { row: number; col: number }> = {
  巳: { row: 1, col: 1 },
  午: { row: 1, col: 2 },
  未: { row: 1, col: 3 },
  申: { row: 1, col: 4 },
  辰: { row: 2, col: 1 },
  酉: { row: 2, col: 4 },
  卯: { row: 3, col: 1 },
  戌: { row: 3, col: 4 },
  寅: { row: 4, col: 1 },
  丑: { row: 4, col: 2 },
  子: { row: 4, col: 3 },
  亥: { row: 4, col: 4 },
};

export function branchPosition(branch: string): [number, number, number] | null {
  const pos = BRANCH_GRID[branch];
  if (!pos) return null;
  return [(pos.col - 2.5) * CELL_W, 0, (pos.row - 2.5) * CELL_D];
}

/** 四化配色（与 2D MUTAGEN_STYLES 同义，给 three 用的 hex） */
export const MUTAGEN_COLORS: Record<string, string> = {
  禄: "#10b981",
  权: "#d97706",
  科: "#0284c7",
  忌: "#e11d48",
};

export const SOUL_EDGE = "#fbbf24";
export const PLATE_EDGE = "#8b5cf6";
```

- [ ] **Step 2: 单宫殿板组件**

创建 `frontend/src/components/ziwei/scene3d/palace-plate.tsx`：

```tsx
"use client";

import { useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import { Text } from "@react-three/drei";
import * as THREE from "three";
import type { ZiweiPalace } from "@/lib/ziwei/types";
import { CELL_W, CELL_D, PLATE_H, PLATE_EDGE, SOUL_EDGE, branchPosition } from "./layout";
import { ZIWEI_FONT_URL, ZIWEI_GLYPHS } from "./glyphs";

export type PalacePlateProps = {
  palace: ZiweiPalace;
  isSoulPalace: boolean;
  dimmed: boolean;
  onSelect: (branch: string) => void;
};

export function PalacePlate({ palace, isSoulPalace, dimmed, onSelect }: PalacePlateProps) {
  const position = branchPosition(palace.earthlyBranch);
  const [hovered, setHovered] = useState(false);
  const matRef = useRef<THREE.MeshStandardMaterial>(null);

  useFrame((_, delta) => {
    if (!matRef.current) return;
    const target = dimmed ? 0.04 : hovered ? 0.5 : isSoulPalace ? 0.3 : 0.16;
    matRef.current.emissiveIntensity = THREE.MathUtils.lerp(matRef.current.emissiveIntensity, target, delta * 6);
    const targetOpacity = dimmed ? 0.25 : 1;
    matRef.current.opacity = THREE.MathUtils.lerp(matRef.current.opacity, targetOpacity, delta * 6);
  });

  if (!position) return null;
  const edgeColor = isSoulPalace ? SOUL_EDGE : PLATE_EDGE;

  return (
    <group position={position}>
      {/* 殿板 */}
      <mesh
        onClick={(e) => {
          e.stopPropagation();
          onSelect(palace.earthlyBranch);
        }}
        onPointerOver={(e) => {
          e.stopPropagation();
          setHovered(true);
          document.body.style.cursor = "pointer";
        }}
        onPointerOut={() => {
          setHovered(false);
          document.body.style.cursor = "auto";
        }}
      >
        <boxGeometry args={[CELL_W - 0.22, PLATE_H, CELL_D - 0.22]} />
        <meshStandardMaterial
          ref={matRef}
          color="#1a1035"
          emissive={edgeColor}
          emissiveIntensity={0.16}
          transparent
          opacity={1}
          roughness={0.55}
          metalness={0.35}
        />
      </mesh>

      {/* 宫名（板面前缘） */}
      <Text
        font={ZIWEI_FONT_URL}
        characters={ZIWEI_GLYPHS}
        fontSize={0.34}
        color={dimmed ? "#4c3d77" : "#e9ddff"}
        anchorX="right"
        anchorY="bottom"
        position={[CELL_W / 2 - 0.32, PLATE_H / 2 + 0.012, CELL_D / 2 - 0.34]}
        rotation={[-Math.PI / 2, 0, 0]}
      >
        {palace.name}
        {palace.isBodyPalace ? " ·身" : ""}
      </Text>

      {/* 干支 + 大限（板面前缘左侧小字） */}
      <Text
        font={ZIWEI_FONT_URL}
        characters={ZIWEI_GLYPHS}
        fontSize={0.2}
        color={dimmed ? "#3c3060" : "#9d8bd6"}
        anchorX="left"
        anchorY="bottom"
        position={[-CELL_W / 2 + 0.32, PLATE_H / 2 + 0.012, CELL_D / 2 - 0.34]}
        rotation={[-Math.PI / 2, 0, 0]}
      >
        {`${palace.heavenlyStem}${palace.earthlyBranch} · ${palace.decadal.range[0]}-${palace.decadal.range[1]}`}
      </Text>

    </group>
  );
}
```

（Task 5 会在本组件内直接追加星曜光球的排布。）

- [ ] **Step 3: 方盘组件（含中宫）**

创建 `frontend/src/components/ziwei/scene3d/mystic-board.tsx`：

```tsx
"use client";

import { Text } from "@react-three/drei";
import type { ZiweiChart } from "@/lib/ziwei/types";
import { CELL_W, CELL_D, PLATE_H } from "./layout";
import { PalacePlate } from "./palace-plate";
import { ZIWEI_FONT_URL, ZIWEI_GLYPHS } from "./glyphs";

function CenterPlate({ chart }: { chart: ZiweiChart }) {
  const lines = [
    chart.fiveElementsClass,
    chart.chineseDate,
    `公历 ${chart.solarDate}`,
    `农历 ${chart.lunarDate}`,
    `${chart.time}（${chart.timeRange}）`,
    `命主 ${chart.soul} · 身主 ${chart.body}`,
    `${chart.zodiac} · ${chart.sign}`,
  ];
  return (
    <group>
      <mesh position={[0, -0.02, 0]}>
        <boxGeometry args={[CELL_W * 2 - 0.34, PLATE_H, CELL_D * 2 - 0.34]} />
        <meshStandardMaterial color="#08041a" emissive="#fbbf24" emissiveIntensity={0.05} roughness={0.7} metalness={0.3} />
      </mesh>
      {lines.map((line, i) => (
        <Text
          key={line}
          font={ZIWEI_FONT_URL}
          characters={ZIWEI_GLYPHS}
          fontSize={i === 0 ? 0.5 : 0.26}
          color={i === 0 ? "#fde68a" : "#b6a3e0"}
          anchorX="center"
          anchorY="middle"
          position={[0, PLATE_H / 2 + 0.012, -2.1 + i * 0.62 + (i > 0 ? 0.25 : 0)]}
          rotation={[-Math.PI / 2, 0, 0]}
        >
          {line}
        </Text>
      ))}
    </group>
  );
}

export type MysticBoardProps = {
  chart: ZiweiChart;
  selectedBranch: string | null;
  onSelectBranch: (branch: string | null) => void;
  children?: React.ReactNode; // 四化光束等盘级装饰（Task 5）
};

export function MysticBoard({ chart, selectedBranch, onSelectBranch, children }: MysticBoardProps) {
  return (
    <group>
      {chart.palaces.map((palace) => (
        <PalacePlate
          key={palace.earthlyBranch}
          palace={palace}
          isSoulPalace={palace.earthlyBranch === chart.earthlyBranchOfSoulPalace}
          dimmed={selectedBranch !== null && selectedBranch !== palace.earthlyBranch}
          onSelect={(branch) => onSelectBranch(branch)}
        />
      ))}
      <CenterPlate chart={chart} />
      {children}
    </group>
  );
}
```

- [ ] **Step 4: 接入场景**

修改 `scene-3d.tsx`：删除占位 `<Text>`，在 `<Starfield />` 之后加入：

```tsx
<MysticBoard chart={chart} selectedBranch={selectedBranch} onSelectBranch={onSelectBranch} />
```

（同时给 `Scene3D` 解构出 `selectedBranch, onSelectBranch` 并导入 `MysticBoard`。）

- [ ] **Step 5: 验证 + Commit**

Run: `cd frontend; npx tsc --noEmit; npm run build` — 无错误。
浏览器：12 块殿板按地支位排布 + 中宫信息板；悬停殿板亮起、指针变手型；命宫金色描边发光；文字朝上贴板可读。

```bash
git add frontend/src/components/ziwei/scene3d/
git commit -m "feat(ziwei): 3D mystic board with palace plates and center info"
```

---

### Task 5: 星曜光球 + 四化光束

**Files:**
- Create: `frontend/src/components/ziwei/scene3d/star-orb.tsx`
- Create: `frontend/src/components/ziwei/scene3d/sihua-beams.tsx`
- Modify: `frontend/src/components/ziwei/scene3d/palace-plate.tsx`（板上渲染光球）
- Modify: `frontend/src/components/ziwei/scene3d/mystic-board.tsx`（挂光束）
- Modify: `frontend/src/components/ziwei/scene3d/scene-3d.tsx`（传 quality 给 board 以控制光束动画）

- [ ] **Step 1: 星曜光球组件**

创建 `frontend/src/components/ziwei/scene3d/star-orb.tsx`：

```tsx
"use client";

import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Text } from "@react-three/drei";
import * as THREE from "three";
import type { ZiweiStar } from "@/lib/ziwei/types";
import { MUTAGEN_COLORS } from "./layout";
import { ZIWEI_FONT_URL, ZIWEI_GLYPHS } from "./glyphs";

export type StarOrbProps = {
  star: ZiweiStar;
  major: boolean;
  position: [number, number, number];
  dimmed: boolean;
};

export function StarOrb({ star, major, position, dimmed }: StarOrbProps) {
  const groupRef = useRef<THREE.Group>(null);
  const phase = useMemo(() => Math.random() * Math.PI * 2, []);
  const radius = major ? 0.17 : 0.1;
  const orbColor = major ? "#ffd9a0" : "#b9a8ef";
  const mutagenColor = star.mutagen ? MUTAGEN_COLORS[star.mutagen] : undefined;

  useFrame(({ clock }) => {
    if (!groupRef.current) return;
    groupRef.current.position.y = position[1] + Math.sin(clock.getElapsedTime() * 1.4 + phase) * 0.06;
  });

  return (
    <group ref={groupRef} position={position}>
      <mesh>
        <sphereGeometry args={[radius, 20, 20]} />
        <meshStandardMaterial
          color={orbColor}
          emissive={mutagenColor ?? orbColor}
          emissiveIntensity={dimmed ? 0.1 : major ? 1.6 : 0.9}
          transparent
          opacity={dimmed ? 0.3 : 1}
        />
      </mesh>
      {/* 四化光环 */}
      {mutagenColor ? (
        <mesh rotation={[-Math.PI / 2, 0, 0]}>
          <torusGeometry args={[radius + 0.07, 0.018, 10, 36]} />
          <meshBasicMaterial color={mutagenColor} transparent opacity={dimmed ? 0.15 : 0.9} />
        </mesh>
      ) : null}
      {/* 星名（含亮度），始终朝上贴板风格改为竖立面向前方便总览阅读 */}
      <Text
        font={ZIWEI_FONT_URL}
        characters={ZIWEI_GLYPHS}
        fontSize={major ? 0.24 : 0.17}
        color={dimmed ? "#4c3d77" : major ? "#ffe9c4" : "#c9b9ef"}
        anchorX="center"
        anchorY="top"
        position={[0, -radius - 0.08, 0]}
        rotation={[-Math.PI / 2, 0, 0]}
      >
        {star.brightness ? `${star.name}·${star.brightness}` : star.name}
      </Text>
    </group>
  );
}
```

- [ ] **Step 2: 殿板上排布光球**

修改 `palace-plate.tsx`：在 `{children}` 之前加入主星/辅星光球排布（主星一排居中靠后，辅星一排在前，超出 4 颗的辅星折行；杂曜不在总览渲染——单宫内景才显示，与 2D 同则）：

```tsx
      {/* 星曜光球：主星排后、辅星排前 */}
      {palace.majorStars.map((star, i) => (
        <StarOrb
          key={star.name}
          star={star}
          major
          dimmed={dimmed}
          position={[(i - (palace.majorStars.length - 1) / 2) * 0.78, 0.46, -CELL_D / 2 + 1.0]}
        />
      ))}
      {palace.minorStars.slice(0, 8).map((star, i) => {
        const perRow = 4;
        const row = Math.floor(i / perRow);
        const indexInRow = i % perRow;
        const rowCount = Math.min(palace.minorStars.length - row * perRow, perRow);
        return (
          <StarOrb
            key={star.name}
            star={star}
            major={false}
            dimmed={dimmed}
            position={[(indexInRow - (rowCount - 1) / 2) * 0.52, 0.32, -CELL_D / 2 + 1.78 + row * 0.5]}
          />
        );
      })}
```

（同时导入 `StarOrb` 与 `CELL_D` 已在作用域。）

- [ ] **Step 3: 四化光束组件**

创建 `frontend/src/components/ziwei/scene3d/sihua-beams.tsx`：

```tsx
"use client";

import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { QuadraticBezierLine } from "@react-three/drei";
import * as THREE from "three";
import type { ZiweiChart } from "@/lib/ziwei/types";
import { MUTAGEN_COLORS, branchPosition } from "./layout";

type BeamSpec = { branch: string; mutagen: string; color: string };

/** 找出生年四化所在的四个宫（扫描全部星曜的 mutagen 标记） */
function findMutagenPalaces(chart: ZiweiChart): BeamSpec[] {
  const beams: BeamSpec[] = [];
  for (const palace of chart.palaces) {
    for (const star of [...palace.majorStars, ...palace.minorStars, ...palace.adjectiveStars]) {
      if (star.mutagen && MUTAGEN_COLORS[star.mutagen]) {
        beams.push({ branch: palace.earthlyBranch, mutagen: star.mutagen, color: MUTAGEN_COLORS[star.mutagen] });
      }
    }
  }
  return beams;
}

function Beam({ spec }: { spec: BeamSpec }) {
  const target = branchPosition(spec.branch);
  // QuadraticBezierLine 的材质透明度做呼吸脉动
  const lineRef = useRef<any>(null);
  useFrame(({ clock }) => {
    const mat = lineRef.current?.material as THREE.Material | undefined;
    if (mat) mat.opacity = 0.35 + (Math.sin(clock.getElapsedTime() * 1.6) + 1) * 0.25;
  });
  if (!target) return null;
  const end: [number, number, number] = [target[0], 0.55, target[2]];
  const mid: [number, number, number] = [target[0] * 0.45, 2.6, target[2] * 0.45];
  return (
    <QuadraticBezierLine
      ref={lineRef}
      start={[0, 0.4, 0]}
      mid={mid}
      end={end}
      color={spec.color}
      lineWidth={2.2}
      transparent
      opacity={0.6}
    />
  );
}

/** 生年四化：自中宫（生辰）飞渡到四化星所在宫的光束 */
export function SihuaBeams({ chart, visible }: { chart: ZiweiChart; visible: boolean }) {
  const beams = useMemo(() => findMutagenPalaces(chart), [chart]);
  if (!visible) return null;
  return (
    <group>
      {beams.map((spec) => (
        <Beam key={`${spec.branch}-${spec.mutagen}`} spec={spec} />
      ))}
    </group>
  );
}
```

注：`lineRef` 上的 `any` 是因为 drei Line ref 类型导出不稳定——实现时先尝试 `Line2` 类型（`three/examples/jsm/lines/Line2`），确实不可行才允许局部 `any` 并注明原因。

- [ ] **Step 4: 接入**

`mystic-board.tsx` 的 `<CenterPlate />` 之后加 `<SihuaBeams chart={chart} visible={selectedBranch === null} />`（飞入单宫时光束隐藏，画面聚焦）。

- [ ] **Step 5: 验证 + Commit**

Run: `cd frontend; npx tsc --noEmit; npm run build` — 无错误。
浏览器：主星大光球+辅星小光球漂浮在殿板上方、带名字与亮度；带四化的星有彩色光环；四条彩色光束从中宫拱向四化宫并呼吸脉动；Bloom 下光球柔和发光。对照档案的 2D 盘核对：每宫星曜与四化与 2D 完全一致。

```bash
git add frontend/src/components/ziwei/scene3d/
git commit -m "feat(ziwei): glowing star orbs and pulsing sihua beams"
```

---

### Task 6: 交互与运镜——飞入单宫、环形殿牌内景、返回

**Files:**
- Create: `frontend/src/components/ziwei/scene3d/camera-rig.tsx`
- Create: `frontend/src/components/ziwei/scene3d/palace-interior.tsx`
- Modify: `frontend/src/components/ziwei/scene3d/scene-3d.tsx`
- Modify: `frontend/src/components/ziwei/chart-view.tsx`（返回按钮 + Esc + 选中宫名提示）

- [ ] **Step 1: 运镜组件**

创建 `frontend/src/components/ziwei/scene3d/camera-rig.tsx`：

```tsx
"use client";

import { useEffect, useRef } from "react";
import { CameraControls } from "@react-three/drei";
import { branchPosition } from "./layout";

const OVERVIEW_POS: [number, number, number] = [0, 12, 10.5];
const OVERVIEW_TARGET: [number, number, number] = [0, 0, 0];

export function useReducedMotion(): boolean {
  if (typeof window === "undefined") return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/** selectedBranch 变化时执行一镜到底运镜；用户拖拽随时可打断（CameraControls 原生支持） */
export function CameraRig({ selectedBranch }: { selectedBranch: string | null }) {
  const controlsRef = useRef<CameraControls>(null);
  const reducedMotion = useReducedMotion();

  useEffect(() => {
    const controls = controlsRef.current;
    if (!controls) return;
    const transition = !reducedMotion;
    if (selectedBranch) {
      const target = branchPosition(selectedBranch);
      if (!target) return;
      void controls.setLookAt(
        target[0] * 1.08,
        3.4,
        target[2] * 1.08 + 2.8,
        target[0],
        0.7,
        target[2],
        transition,
      );
    } else {
      void controls.setLookAt(...OVERVIEW_POS, ...OVERVIEW_TARGET, transition);
    }
  }, [selectedBranch, reducedMotion]);

  return (
    <CameraControls
      ref={controlsRef}
      makeDefault
      minDistance={3}
      maxDistance={28}
      maxPolarAngle={Math.PI * 0.46}
      smoothTime={0.45}
    />
  );
}
```

- [ ] **Step 2: 单宫内景——星曜环形殿牌**

创建 `frontend/src/components/ziwei/scene3d/palace-interior.tsx`：

```tsx
"use client";

import { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Billboard, Text } from "@react-three/drei";
import * as THREE from "three";
import type { ZiweiPalace, ZiweiStar } from "@/lib/ziwei/types";
import { MUTAGEN_COLORS, branchPosition } from "./layout";
import { ZIWEI_FONT_URL, ZIWEI_GLYPHS } from "./glyphs";

function StarTablet({ star, major }: { star: ZiweiStar; major: boolean }) {
  const mutagenColor = star.mutagen ? MUTAGEN_COLORS[star.mutagen] : undefined;
  const w = major ? 0.78 : 0.6;
  const h = major ? 1.16 : 0.92;
  return (
    <Billboard>
      <mesh>
        <planeGeometry args={[w, h]} />
        <meshStandardMaterial
          color="#160b38"
          emissive={mutagenColor ?? "#8b5cf6"}
          emissiveIntensity={major ? 0.5 : 0.3}
          transparent
          opacity={0.92}
          side={THREE.DoubleSide}
        />
      </mesh>
      <Text
        font={ZIWEI_FONT_URL}
        characters={ZIWEI_GLYPHS}
        fontSize={major ? 0.27 : 0.2}
        color={major ? "#ffe9c4" : "#d8c8ff"}
        anchorX="center"
        anchorY="middle"
        position={[0, 0.12, 0.01]}
      >
        {star.name}
      </Text>
      <Text
        font={ZIWEI_FONT_URL}
        characters={ZIWEI_GLYPHS}
        fontSize={0.16}
        color="#9d8bd6"
        anchorX="center"
        anchorY="middle"
        position={[0, -0.24, 0.01]}
      >
        {[star.brightness, star.mutagen ? `化${star.mutagen}` : ""].filter(Boolean).join(" · ") || "—"}
      </Text>
    </Billboard>
  );
}

/** 选中宫位的内景：全部星曜（含杂曜）化作环形殿牌绕宫心旋转 */
export function PalaceInterior({ palace }: { palace: ZiweiPalace }) {
  const center = branchPosition(palace.earthlyBranch);
  const ringRef = useRef<THREE.Group>(null);
  const stars: Array<{ star: ZiweiStar; major: boolean }> = [
    ...palace.majorStars.map((star) => ({ star, major: true })),
    ...palace.minorStars.map((star) => ({ star, major: false })),
    ...palace.adjectiveStars.map((star) => ({ star, major: false })),
  ];

  useFrame((_, delta) => {
    if (ringRef.current) ringRef.current.rotation.y += delta * 0.18;
  });

  if (!center || stars.length === 0) return null;
  const radius = Math.max(1.15, stars.length * 0.21);

  return (
    <group position={[center[0], 1.05, center[2]]}>
      {/* 宫心光核 */}
      <mesh>
        <sphereGeometry args={[0.16, 20, 20]} />
        <meshStandardMaterial color="#fff7df" emissive="#fbbf24" emissiveIntensity={2.2} />
      </mesh>
      <group ref={ringRef}>
        {stars.map(({ star, major }, i) => {
          const angle = (i / stars.length) * Math.PI * 2;
          return (
            <group key={star.name} position={[Math.cos(angle) * radius, 0, Math.sin(angle) * radius]}>
              <StarTablet star={star} major={major} />
            </group>
          );
        })}
      </group>
    </group>
  );
}
```

- [ ] **Step 3: 场景接线**

修改 `scene-3d.tsx`：

1. `<CameraControls ... />` 替换为 `<CameraRig selectedBranch={selectedBranch} />`（导入并删除原 CameraControls 导入）。
2. `<MysticBoard ...>` 之后加：

```tsx
{selectedPalace ? <PalaceInterior palace={selectedPalace} /> : null}
```

其中 `const selectedPalace = chart.palaces.find((p) => p.earthlyBranch === selectedBranch) ?? null;`

3. Canvas 上加「点空白回总览」：`onPointerMissed={() => onSelectBranch(null)}`。

- [ ] **Step 4: ChartView 加返回按钮与 Esc**

修改 `chart-view.tsx`：在 3D 容器内（`<Scene3D />` 同级）加：

```tsx
{show3d && selectedBranch ? (
  <button
    type="button"
    onClick={() => setSelectedBranch(null)}
    className="absolute left-3 top-3 z-10 rounded-full border border-violet-500/40 bg-[#120a2e]/85 px-4 py-1.5 text-xs font-semibold text-violet-100 backdrop-blur transition-colors hover:bg-violet-600/40"
  >
    ← 返回总览
  </button>
) : null}
```

并加 Esc 键支持：

```tsx
useEffect(() => {
  const onKey = (e: KeyboardEvent) => {
    if (e.key === "Escape") setSelectedBranch(null);
  };
  window.addEventListener("keydown", onKey);
  return () => window.removeEventListener("keydown", onKey);
}, []);
```

（`switchMode` 清空选宫已在 Task 2 的修复轮实现，无需重复。）

- [ ] **Step 5: 验证 + Commit**

Run: `cd frontend; npx tsc --noEmit; npm run build` — 无错误。
浏览器全流程：点击官禄宫 → 镜头平滑俯冲贴近该宫，其余宫位变暗、四化光束隐去，宫上方出现缓转的星曜环形殿牌（含杂曜、化曜标注）→ 点「返回总览」/按 Esc/点空白处 → 镜头拉回总览、亮度恢复。系统开启「减少动态效果」时运镜瞬时完成。

```bash
git add frontend/src/components/ziwei/scene3d/ frontend/src/components/ziwei/chart-view.tsx
git commit -m "feat(ziwei): palace fly-in camera rig and orbiting star-tablet interior"
```

---

### Task 7: 打磨与降级完备——入场动画、错误兜底、移动端

**Files:**
- Modify: `frontend/src/components/ziwei/scene3d/scene-3d.tsx`（入场动画 + Canvas 错误兜底回调）
- Modify: `frontend/src/components/ziwei/chart-view.tsx`（渲染异常回退 2D）
- Modify: `frontend/src/components/ziwei/scene3d/mystic-board.tsx`（入场上升渐显）

- [ ] **Step 1: 入场动画（可跳过）**

`mystic-board.tsx`：board 根 group 加入场动画——挂载后 1.2 秒内从 y=-1.2 升到 0、整体材质透明度随之渐入；`prefers-reduced-motion` 或任何一次用户点击立即跳到终态：

```tsx
const groupRef = useRef<THREE.Group>(null);
const progressRef = useRef(0);
const reducedMotion = useReducedMotion();

useFrame((_, delta) => {
  if (!groupRef.current) return;
  if (reducedMotion) progressRef.current = 1;
  progressRef.current = Math.min(1, progressRef.current + delta / 1.2);
  const eased = 1 - Math.pow(1 - progressRef.current, 3);
  groupRef.current.position.y = -1.2 * (1 - eased);
});
```

（根 `<group ref={groupRef}>` 包住现有内容；导入 `useReducedMotion` from `./camera-rig`、`useFrame`、`useRef`、`THREE` 视需要。点击跳过：`ChartView` 的容器 `onPointerDown` 时通过一个 `skipIntroRef` 信号——实现时若跨组件传递复杂，可简化为「reduced-motion 跳过 + 动画时长仅 1.2s」并在汇报中注明取舍。）

- [ ] **Step 2: 渲染异常回退 2D**

`chart-view.tsx`：加 `renderFailed` state；传给 3D 容器一个 `onRenderError` 回调。`scene-3d.tsx` 的 `<Canvas onCreated={...}>` 用 `gl.getContext().isContextLost()` 初检，并监听 `webglcontextlost`：

```tsx
onCreated={({ gl }) => {
  gl.domElement.addEventListener("webglcontextlost", () => onRenderError?.(), { once: true });
}}
```

`Scene3DProps` 增加可选 `onRenderError?: () => void`；ChartView 里 `renderFailed === true` 时强制走 2D 分支并显示提示「3D 渲染中断，已切换 2D 命盘」。

- [ ] **Step 3: 移动端核对（代码内已覆盖，逐项确认）**

- CameraControls 原生支持单指旋转/双指缩放——无需额外代码，确认即可
- 3D 容器高度 `h-[72vh] min-h-[480px]` 在窄屏可用
- 返回按钮与模式切换按钮触达尺寸 ≥ 32px

- [ ] **Step 4: 验证 + Commit**

Run: `cd frontend; npx tsc --noEmit; npm run build` — 无错误。
浏览器：刷新见方盘自下而上升起渐显（约 1.2s）；DevTools 里手动触发 `webglcontextlost`（`canvas.getContext('webgl2').getExtension('WEBGL_lose_context').loseContext()`）→ 自动回退 2D 并出提示；370px 视口下布局可用、可单指转盘。

```bash
git add frontend/src/components/ziwei/
git commit -m "feat(ziwei): entrance animation, webgl context-loss fallback, mobile polish"
```

---

### Task 8: 收尾——E2E、文档勘误、全量验证

- [ ] **Step 1: spec 勘误**

`docs/superpowers/specs/2026-06-09-ziwei-3d-design.md` §9 中「降级为精美 2D 命盘（SVG 方盘）」改为「降级为精美 2D 命盘（HTML/CSS 方盘，Phase 1 已实现）」（Phase 1 评审遗留的措辞修正）。

- [ ] **Step 2: 全量验证**

```
cd backend; python -m pytest tests/ --ignore=tests/test_api.py -q     → 全 PASS（后端零改动，防回归）
cd frontend; npx tsc --noEmit                                          → 无错误
cd frontend; node scripts/ziwei-smoke.cjs                              → SMOKE OK
cd frontend; npm run build                                             → 无错误，注意记录 /ziwei 首载 JS 体积（对比 Phase 1 的 256kB——3D 在独立 chunk，首载不应明显增长）
```

- [ ] **Step 3: E2E（controller 用 preview 工具执行）**

1. 建档（或用既有档案）→ 默认 3D：星空+方盘+光球+光束齐全，与 2D 数据一致
2. 点宫飞入 → 环形殿牌 → Esc 返回
3. 切 2D → 刷新记住偏好 → 切回 3D
4. 模拟 WebGL 丢失 → 自动回退 2D
5. 移动端视口（390×844）：可转盘、可飞入、按钮可点

- [ ] **Step 4: 提交遗留 + 汇报**

```bash
git status
git add -A
git commit -m "chore(ziwei): phase 2 final polish"
```

汇报：验证结果、与计划偏差、/ziwei bundle 数据。

---

## 后续阶段衔接

- `selectedBranch` 状态与 `CameraRig` 是 Phase 3「AI 镜头指令」的落点：oracle 输出 `focus_palace(宫名)` → 宫名转地支 → set `selectedBranch`。
- `PalaceInterior` 的殿牌区将在 Phase 3 扩展「该宫格局解读卡」。
- 流年（Phase 5）将在 `layout.ts` 基础上叠加流年层光环，勿在本阶段预留空代码（YAGNI）。
