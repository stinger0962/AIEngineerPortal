/** 归一化命盘 JSON —— 存入后端 ZiweiProfile.chart_json，渲染与 AI 共用此结构 */

export type ZiweiStar = {
  name: string;
  /** major | soft | tough | adjective | flower | helper | lucun | tianma */
  type: string;
  /** 庙|旺|得|利|平|不|陷，可能为空 */
  brightness?: string;
  /** 禄|权|科|忌（生年四化），无则为空 */
  mutagen?: string;
};

export type ZiweiPalace = {
  index: number;
  name: string;
  isBodyPalace: boolean;
  isOriginalPalace: boolean;
  heavenlyStem: string;
  earthlyBranch: string;
  majorStars: ZiweiStar[];
  minorStars: ZiweiStar[];
  adjectiveStars: ZiweiStar[];
  changsheng12: string;
  decadal: { range: [number, number]; heavenlyStem: string; earthlyBranch: string };
  ages: number[];
};

export type ZiweiChart = {
  gender: string;
  solarDate: string;
  lunarDate: string;
  chineseDate: string;
  time: string;
  timeRange: string;
  sign: string;
  zodiac: string;
  earthlyBranchOfSoulPalace: string;
  earthlyBranchOfBodyPalace: string;
  soul: string;
  body: string;
  fiveElementsClass: string;
  palaces: ZiweiPalace[];
};

export type BirthInput = {
  /** 公历或农历日期，YYYY-M-D */
  dateStr: string;
  /** 时辰 0-12（0=早子时, 12=晚子时） */
  timeIndex: number;
  gender: "male" | "female";
  isLunar: boolean;
  isLeapMonth?: boolean;
};
