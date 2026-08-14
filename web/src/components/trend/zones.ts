/* ------------------------------------------------------------------ *
 * 基本面趋势图共享层：阈值框架 + 分界线 + 区间着色。
 *
 * 单一事实源——FundamentalsPage 的趋势抽屉与 WorkspacePage 的
 * MacroSnapshotPanel 共用同一套研究归纳的阈值，避免两处漂移。
 * 阈值为研究机构公开观点的综合归纳，非交易指令。
 * ------------------------------------------------------------------ */

export type Tone = "opportunity" | "neutral" | "caution" | "warning" | "danger";

export interface ZoneLevel {
  max: number;
  label: string;
  tone: Tone;
  note: string;
}

export interface MarkLine {
  y: number;
  label: string;
  color: string;
}

/** 多线趋势图的线配置（如宽度 20/50/200）。 */
export interface LineSeriesConfig {
  name: string;
  color: string;
}

export function zoneToneColor(tone: Tone): string {
  switch (tone) {
    case "opportunity":
      return "#16a34a"; // green
    case "neutral":
      return "#6b7280"; // gray
    case "caution":
      return "#f59e0b"; // amber
    case "warning":
      return "#ea580c"; // orange
    case "danger":
      return "#dc2626"; // red
    default:
      return "#6b7280";
  }
}

export function findZone(
  value: number | null,
  zones: readonly ZoneLevel[],
): ZoneLevel {
  if (value == null) return zones[0];
  return zones.find((z) => value <= z.max) ?? zones[zones.length - 1];
}

/* ---- 各指标区间框架（带研究出处）---- */

/** 美国 10Y 国债收益率风险区间 */
export const US_10Y_ZONES: readonly ZoneLevel[] = [
  { max: 3.5, label: "宽松/衰退信号", tone: "opportunity", note: "< 3.5%：美债避险需求强，通常对应经济放缓或衰退预期（BofA Hartnett，2025.03）" },
  { max: 4.0, label: "中性偏松", tone: "neutral", note: "3.5–4.0%：货币政策偏鸽，对股市估值压力有限" },
  { max: 4.5, label: "甜蜜点区间", tone: "caution", note: "4.0–4.5%：Morgan Stanley 称为美股估值「甜蜜点」（2025.01）" },
  { max: 4.75, label: "压力区", tone: "warning", note: "4.5–4.75%：Evercore ISI 指出突破此区将导致「更长更深的调整」（2024.12）" },
  { max: Infinity, label: "危险区", tone: "danger", note: "> 5.0%：Evercore ISI 警戒线，对周期性牛市构成重大威胁；2018年触发点为 3%，本轮周期阈值上移至 5%" },
];

/** 中国 10Y 国债收益率风险区间 */
export const CN_10Y_ZONES: readonly ZoneLevel[] = [
  { max: 1.8, label: "极度宽松/资产荒", tone: "opportunity", note: "< 1.8%：10Y 破「2」进入 1 字头时代（2024.12），资产荒加剧，权益相对性价比提升（招商策略）" },
  { max: 2.2, label: "合理区间", tone: "neutral", note: "1.8–2.2%：平安理财预期 2025 年运行区间；开源证券 H2 目标 1.9–2.2%（DR007+40~70bp 历史中枢）" },
  { max: 2.5, label: "偏紧缩", tone: "caution", note: "2.2–2.5%：若通胀正常化 DR007 回升至 1.8%，对应 10Y 或达 2.5%（开源证券）" },
  { max: Infinity, label: "明显收紧", tone: "warning", note: "> 2.5%：货币政策转向收紧信号，对成长股估值构成压制" },
];

/** 中美 10 年利差（CN − US）区间 */
export const CN_US_SPREAD_ZONES: readonly ZoneLevel[] = [
  { max: -1, label: "深度倒挂", tone: "danger", note: "< -1%：美债收益远高于中债，资本外流与人民币贬值压力显著" },
  { max: 0, label: "倒挂", tone: "warning", note: "< 0%：美债收益更高，资本外流压力侧；倒挂加深常伴人民币贬值压力" },
  { max: 0.5, label: "收窄", tone: "caution", note: "0–0.5%：中美利差接近，吸引力相当" },
  { max: Infinity, label: "正常溢价", tone: "neutral", note: "> 0.5%：中债收益溢价，资金倾向留驻" },
];

/** 两融余额风险区间（单位：亿元） */
export const MARGIN_ZONES: readonly ZoneLevel[] = [
  { max: 15000, label: "低杠杆/情绪谨慎", tone: "caution", note: "< 1.5万亿：市场参与度低，可能处于底部区域但也反映信心不足" },
  { max: 22000, label: "正常区间", tone: "neutral", note: "1.5–2.2万亿：历史常态区间；2015 年前峰值 2.27 万亿" },
  { max: 28000, label: "偏高但可控", tone: "warning", note: "2.2–2.8万亿：绝对值偏高但占流通市值比仍 < 3%（2025 年 6 月 3 万亿时仅 2.83%）" },
  { max: Infinity, label: "警戒线附近", tone: "danger", note: "> 2.8万亿 / 占流通市值 > 4%：接近 2015 年股灾前水平（当时 4.27%）；需高度警惕结构性拥挤与强平风险（银河证券、格上基金）" },
];

/** VIX 恐慌指数区间 */
export const VIX_ZONES: readonly ZoneLevel[] = [
  { max: 15, label: "低波动/乐观", tone: "opportunity", note: "< 15：市场情绪偏乐观，但也可能意味着自满" },
  { max: 20, label: "正常", tone: "neutral", note: "15–20：正常波动区间" },
  { max: 30, label: "升高", tone: "caution", note: "20–30：波动升高，风险偏好下降" },
  { max: Infinity, label: "恐慌", tone: "danger", note: "> 30：市场系统性风险偏高，恐慌情绪蔓延" },
];

/** 市场宽度区间（% 站上均线的个股占比） */
export const BREADTH_ZONES: readonly ZoneLevel[] = [
  { max: 15, label: "超卖/短期底部", tone: "opportunity", note: "< 15%：宽度极低，大概率短期底部；配合 200 日同低可能见反转" },
  { max: 50, label: "中性偏弱", tone: "caution", note: "15–50%：上涨面不足，偏弱" },
  { max: 85, label: "偏热", tone: "neutral", note: "50–85%：上涨面扩大，正常偏强" },
  { max: Infinity, label: "超买/阶段顶部", tone: "danger", note: "> 85%：大概率阶段性顶部" },
];

/** 制造业 PMI 区间（荣枯线 50） */
export const PMI_ZONES: readonly ZoneLevel[] = [
  { max: 49, label: "收缩", tone: "warning", note: "< 49：制造业处于收缩区间，景气偏弱" },
  { max: 50, label: "荣枯线附近", tone: "caution", note: "49–50：荣枯线附近，景气待确认" },
  { max: 53, label: "温和扩张", tone: "neutral", note: "50–53：温和扩张" },
  { max: Infinity, label: "强劲扩张", tone: "opportunity", note: "> 53：扩张动能强劲" },
];

/** CPI 同比区间 */
export const CPI_ZONES: readonly ZoneLevel[] = [
  { max: 0, label: "通缩", tone: "warning", note: "< 0：CPI 同比为负，通缩压力，需求不足" },
  { max: 1, label: "低通胀", tone: "opportunity", note: "0–1%：温和，货币政策空间充裕" },
  { max: 3, label: "正常", tone: "neutral", note: "1–3%：正常通胀区间" },
  { max: Infinity, label: "高通胀", tone: "danger", note: "> 3%：通胀偏高，货币收紧压力" },
];

/** PPI 同比区间 */
export const PPI_ZONES: readonly ZoneLevel[] = [
  { max: 0, label: "通缩", tone: "warning", note: "< 0：PPI 同比为负，工业品价格下行" },
  { max: 3, label: "温和回升", tone: "neutral", note: "0–3%：温和回升" },
  { max: Infinity, label: "工业品过热", tone: "caution", note: "> 3%：工业品价格偏热" },
];

/* ---- 各指标趋势图分界线（与上方区间框架一致）---- */

export const MARKLINES: Record<string, MarkLine[]> = {
  us_10y: [
    { y: 3.5, label: "3.5 宽松", color: "#16a34a" },
    { y: 4.5, label: "4.5 甜蜜点", color: "#f59e0b" },
    { y: 5.0, label: "5.0 危险", color: "#dc2626" },
  ],
  cn_10y: [
    { y: 1.8, label: "1.8 资产荒", color: "#16a34a" },
    { y: 2.2, label: "2.2 合理", color: "#6b7280" },
    { y: 2.5, label: "2.5 收紧", color: "#f59e0b" },
  ],
  cn_us_spread_10y: [
    { y: 0, label: "0 多空分界", color: "#6b7280" },
    { y: -1, label: "-1 深度倒挂", color: "#dc2626" },
  ],
  vix: [
    { y: 15, label: "15 低波动", color: "#16a34a" },
    { y: 20, label: "20 正常", color: "#6b7280" },
    { y: 30, label: "30 恐慌", color: "#dc2626" },
  ],
  margin_rzrqye: [
    { y: 15000, label: "1.5万亿", color: "#f59e0b" },
    { y: 22000, label: "2.2万亿", color: "#6b7280" },
    { y: 28000, label: "2.8万亿", color: "#dc2626" },
  ],
  breadth: [
    { y: 15, label: "15 超卖", color: "#16a34a" },
    { y: 50, label: "50 多空分界", color: "#6b7280" },
    { y: 85, label: "85 超买", color: "#dc2626" },
  ],
  pmi: [{ y: 50, label: "50 荣枯线", color: "#6b7280" }],
  cpi: [{ y: 0, label: "0 通胀/通缩", color: "#6b7280" }],
  ppi: [{ y: 0, label: "0 通胀/通缩", color: "#6b7280" }],
};

/* ---- 宽度多线配置（20/50/200）---- */
export const BREADTH_LINES: LineSeriesConfig[] = [
  { name: "20日", color: "#ea580c" },
  { name: "50日", color: "#3a7bd5" },
  { name: "200日", color: "#7c3aed" },
];

/** 各指标区间图例（供抽屉侧栏展示）。 */
export const ZONES: Record<string, readonly ZoneLevel[]> = {
  us_10y: US_10Y_ZONES,
  cn_10y: CN_10Y_ZONES,
  cn_us_spread_10y: CN_US_SPREAD_ZONES,
  vix: VIX_ZONES,
  margin_rzrqye: MARGIN_ZONES,
  breadth: BREADTH_ZONES,
  pmi: PMI_ZONES,
  cpi: CPI_ZONES,
  ppi: PPI_ZONES,
};
