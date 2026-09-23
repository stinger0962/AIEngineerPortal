export type PipelineNode = {
  id: number;
  title: string;
  phase: string;
  input: string;
  machine: string;
  output: string;
  gate: string;
  gateBranches?: string[];
  isPre?: boolean;
};

export const PIPELINE_NODES: PipelineNode[] = [
  {
    id: 0,
    title: "期刊指纹",
    phase: "前置",
    input: "目标期刊名单（5–8 家）",
    machine: "批量取文（2024–2026）→ 结构化抽取 → 输出选题地图 / 结构模板 / 方法画像 / 审稿人清单",
    output: "《目标期刊指纹报告》",
    gate: "确认投稿目标期刊",
    isPre: true,
  },
  {
    id: 1,
    title: "选题",
    phase: "第 1 步",
    input: "指纹报告 + 博士论文方向 + 导师课题",
    machine: "生成 10 个候选题卡（研究问题 · 贡献点 · 数据需求 · 相近已发文章 ×3）",
    output: "10 张选题卡",
    gate: "选定题目，导师确认（选题错了后面全白做）",
  },
  {
    id: 2,
    title: "文献入库",
    phase: "第 2 步",
    input: "知网题录 + PDF 全文",
    machine: "Zotero 入库 → 每篇一张模板笔记（问题 · 方法 · 结论 · 可引用句 · 与本文关系）",
    output: "笔记库",
    gate: "扫一遍笔记，删不相关的",
  },
  {
    id: 3,
    title: "综述",
    phase: "第 3 步",
    input: "笔记库",
    machine: "按“主题 → 分歧 → 缺口”生成综述骨架，每句带引用编号",
    output: "综述骨架",
    gate: "重写（机器版只是骨架）",
  },
  {
    id: 4,
    title: "框架与命题",
    phase: "第 4 步",
    input: "综述 + 选题",
    machine: "给出 2–3 套理论框架方案 + 命题/假说 + 对应实证设计",
    output: "框架方案文档",
    gate: "拍板（观点是她的，机器不插手）",
  },
  {
    id: 5,
    title: "实证",
    phase: "第 5 步",
    input: "命题 + 数据",
    machine: "数据清洗 → 建模 → 三线表 / 图（黑白可读 · 300dpi）+ 一页结果说明",
    output: "表、图、结果说明",
    gate: "解读系数（数字是机器的，意思是她的）",
  },
  {
    id: 6,
    title: "初稿",
    phase: "第 6 步",
    input: "以上全部 + 指纹结构模板",
    machine: "按目标期刊结构拼完整初稿，每段标注 [机器写] / [人工写]",
    output: "完整初稿",
    gate: "逐段重写机器段落（去 AI 痕迹，不是润色）",
  },
  {
    id: 7,
    title: "自审",
    phase: "第 7 步",
    input: "初稿 + 审稿人清单",
    machine: "三个审稿人角色（理论派 · 实证派 · 格式派）各写审稿意见 + 对清单逐条打勾 + 查重 + AIGC 检测",
    output: "审稿报告",
    gate: "分支判断",
    gateBranches: [
      "自审通过 → 进入第 8 步",
      "未通过 → 打回第 4 步（框架与命题）重做",
      "查重 / AIGC 超标 → 暂停，等处理后再继续",
    ],
  },
  {
    id: 8,
    title: "导师 → 投稿 → 返修",
    phase: "第 8 步",
    input: "导师意见 / 外审意见",
    machine: "拆成逐条任务 → 回复信初稿（一意见 · 一段回应 · 一处修改）→ 排版 · 参考文献终检",
    output: "修改稿 + 回复信",
    gate: "定回复口径",
  },
];

export const PIPELINE_META = {
  title: "论文工厂",
  subtitle: "C 刊论文全自动写作流水线",
  tagline: "自动推进 · 人工闸门 · 到点停下等确认，确认后继续 —— 不断 loop",
  mechanics: [
    { k: "状态机", v: "每道工序 待跑 → 运行中 → 等人工 → 已完成，全自动流转，不用人盯着" },
    { k: "通知", v: "每个里程碑 / 闸门触发时主动推送；随时可问“跑到哪了”" },
    { k: "红线", v: "不编造数据 · 不代写观点 · 机器段落必须人工重写 · 按期刊要求声明 AI 使用" },
  ],
};
