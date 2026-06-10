import { astro } from "iztro";
import type { IFunctionalPalace } from "iztro/lib/astro/FunctionalPalace";
import type { IFunctionalStar } from "iztro/lib/star/FunctionalStar";
import type { BirthInput, ZiweiChart, ZiweiPalace, ZiweiStar } from "./types";

function toStar(star: IFunctionalStar): ZiweiStar {
  return {
    name: star.name,
    type: star.type,
    brightness: star.brightness || undefined,
    mutagen: star.mutagen || undefined,
  };
}

function toPalace(p: IFunctionalPalace): ZiweiPalace {
  return {
    index: p.index,
    name: p.name,
    isBodyPalace: p.isBodyPalace,
    isOriginalPalace: p.isOriginalPalace,
    heavenlyStem: p.heavenlyStem,
    earthlyBranch: p.earthlyBranch,
    majorStars: p.majorStars.map(toStar),
    minorStars: p.minorStars.map(toStar),
    adjectiveStars: p.adjectiveStars.map(toStar),
    changsheng12: p.changsheng12,
    decadal: {
      range: [p.decadal.range[0], p.decadal.range[1]],
      heavenlyStem: p.decadal.heavenlyStem,
      earthlyBranch: p.decadal.earthlyBranch,
    },
    ages: [...p.ages],
  };
}

/** 浏览器内排盘：iztro 星盘 → 归一化 ZiweiChart（可 JSON 序列化，存入档案） */
export function computeChart(input: BirthInput): ZiweiChart {
  const gender = input.gender === "female" ? "女" : "男";
  const astrolabe = input.isLunar
    ? astro.byLunar(input.dateStr, input.timeIndex, gender, input.isLeapMonth ?? false, true, "zh-CN")
    : astro.bySolar(input.dateStr, input.timeIndex, gender, true, "zh-CN");

  return {
    gender: astrolabe.gender,
    solarDate: astrolabe.solarDate,
    lunarDate: astrolabe.lunarDate,
    chineseDate: astrolabe.chineseDate,
    time: astrolabe.time,
    timeRange: astrolabe.timeRange,
    sign: astrolabe.sign,
    zodiac: astrolabe.zodiac,
    earthlyBranchOfSoulPalace: astrolabe.earthlyBranchOfSoulPalace,
    earthlyBranchOfBodyPalace: astrolabe.earthlyBranchOfBodyPalace,
    soul: astrolabe.soul,
    body: astrolabe.body,
    fiveElementsClass: String(astrolabe.fiveElementsClass),
    palaces: astrolabe.palaces.map(toPalace),
  };
}
