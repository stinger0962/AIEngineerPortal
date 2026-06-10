/**
 * 生成 3D 场景用的中文字体子集（troika-three-text 不支持 woff2，输出 woff）。
 * 字形来源：精选常量（覆盖星曜/宫位/干支/亮度/四化/农历/UI）∪ iztro zh-CN локале 能找到的字符串。
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
  if (woff.length > 400 * 1024) throw new Error("子集异常偏大（>400KB），检查字形集是否混入大量无关字符");
})();
