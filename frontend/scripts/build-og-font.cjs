/*
 * 为 OG 分享配图子集化 Noto Sans SC。
 * 产物：src/app/_og/og-font.ttf（仅含卡片用到的字形，几 KB，入库）。
 * 用法：node scripts/build-og-font.cjs [本地 NotoSansSC-Regular.otf 路径]
 *      不传则从 googlefonts/noto-cjk 下载（约16MB，仅本次用，不入库）。
 */
const fs = require("fs");
const path = require("path");
const os = require("os");
const subsetFont = require("subset-font");

const FONT_URL =
  "https://raw.githubusercontent.com/googlefonts/noto-cjk/main/Sans/SubsetOTF/SC/NotoSansSC-Regular.otf";
const OUT = path.join(__dirname, "..", "public", "fonts", "og-font.ttf");

// 必须覆盖卡片渲染到的每一个字符，否则显示豆腐块。宁可多包。
const TEXT = [
  "蒸馏所", "Distill", "万物皆可蒸馏", "Distill anything",
  "炼 Forge", "视频", "播客",
  "织 Loom", "内容", "摘要",
  "录 Scribe", "文字稿",
  "配 Dub", "外语视频", "中文配音",
  "AI Engineer Portal", "portal.leipan.cc",
  "·", "→", "—",
  "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.",
].join("");

async function getSource(localPath) {
  if (localPath) return fs.readFileSync(localPath);
  const tmp = path.join(os.tmpdir(), "NotoSansSC-Regular.otf");
  if (fs.existsSync(tmp)) return fs.readFileSync(tmp);
  console.log("下载 Noto Sans SC（约16MB，仅本次使用）……");
  const res = await fetch(FONT_URL);
  if (!res.ok) throw new Error(`下载失败 ${res.status}：可手动下载后 node scripts/build-og-font.cjs <路径>`);
  const buf = Buffer.from(await res.arrayBuffer());
  fs.writeFileSync(tmp, buf);
  return buf;
}

(async () => {
  const source = await getSource(process.argv[2]);
  const ttf = await subsetFont(source, TEXT, { targetFormat: "truetype" });
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  fs.writeFileSync(OUT, ttf);
  console.log(`✓ 写出 ${OUT}（${(ttf.length / 1024).toFixed(1)} KB，${[...new Set(TEXT)].length} 唯一字符）`);
})();
