/**
 * 回测报告统一归档索引 —— 多路回测 AI 共同写入的唯一入口。
 *
 * 规约（新增报告时必须遵守）：
 * 1. 只允许【追加条目】，不删不改别人的条目；
 * 2. href 必须指向 web/public/reports/ 下已存在的自包含 HTML（离线双击可开）；
 * 3. oneLine 必须带完整口径：核心数字 + 时间窗 + 费用假设，不许只写好数字；
 * 4. 证伪实验（status: falsified）同样必须归档——证伪档案和通过档案同等重要；
 * 5. 原始数据落 docs/experiments/raw/<team>/，报告尾部注明复现命令。
 */
export interface ReportEntry {
  id: string;    // 唯一标识：<team>-<主题>
  team: string;  // 归档方标识，如 "宽度组" / "ETF组" / "LEI组"
  title: string; // 页面显示名（含日期）
  href: string;  // /reports/xxx.html（web/public/reports/ 下）
  date: string;  // 生成日期 YYYY-MM-DD
  topic: string; // 主题：宽度择时/ETF/个股/仓位管理/美股/验证方法…
  status: "passed" | "falsified" | "mixed" | "watch";
  oneLine: string; // 一句话核心结论，口径必须完整
}

export const REPORTS_INDEX: ReportEntry[] = [
  {
    id: "breadth-flagship",
    team: "宽度组",
    title: "旗舰三组合总览（净值·买卖点·仓位带）",
    href: "/reports/flagship-2026-09-01.html",
    date: "2026-09-01",
    topic: "宽度择时",
    status: "passed",
    oneLine: "两只版 15.9%/-25.6%/Calmar 0.62（16.2年全周期,10bp双边,事后选腿折让后预期11-12%）；ETF可交易版 12.5%/-20.1%",
  },
  {
    id: "breadth-duo-trades",
    team: "宽度组",
    title: "两只版逐笔调仓明细（139 笔）",
    href: "/reports/duo-trades-2026-09-01.html",
    date: "2026-09-01",
    topic: "宽度择时",
    status: "passed",
    oneLine: "创业板×三档(43.3/56.7)+虹吸+纳指持有，周频信号次日执行，16年139笔，约1.4个月/次",
  },
  {
    id: "breadth-round-0831",
    team: "宽度组",
    title: "总报告：宽度/ETF/虹吸全档案",
    href: "/reports/round-2026-08-31.html",
    date: "2026-08-31",
    topic: "宽度择时",
    status: "mixed",
    oneLine: "M1流动性轴判负、融资余额虹吸双池全过、14行业适配地图、16+项证伪档案全记录",
  },
  {
    id: "breadth-round-0828",
    team: "宽度组",
    title: "总报告：B 形态终审矩阵（8 道全过）",
    href: "/reports/round-2026-08-28.html",
    date: "2026-08-28",
    topic: "验证方法",
    status: "passed",
    oneLine: "B9九池认证：起点偏移31/31、参数高原24/24无孤峰、留一、安慰剂第100分位",
  },
];
