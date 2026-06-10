// 验证 iztro 排盘核心 API（文档示例盘：2000-8-16 寅时 女）
const { astro } = require("iztro");

const a = astro.bySolar("2000-8-16", 2, "女", true, "zh-CN");
console.log("palaces:", a.palaces.length);
console.log("fiveElementsClass:", a.fiveElementsClass);
console.log("soul/body:", a.soul, a.body);
console.log("palace0:", a.palaces[0].name, a.palaces[0].earthlyBranch, a.palaces[0].majorStars.map((s) => s.name + (s.mutagen || "")).join(","));

const h = a.horoscope("2026-6-9");
console.log("decadal:", h.decadal.name, h.decadal.mutagen.join(","));
console.log("yearly:", h.yearly.name, h.yearly.mutagen.join(","));

if (a.palaces.length !== 12) throw new Error("expected 12 palaces");
console.log("SMOKE OK");
