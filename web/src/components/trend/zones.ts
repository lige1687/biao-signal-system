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

/** 美国 10Y 国债收益率风险区间
 *
 * 机理：美债 10Y 是全球资产定价之锚（无风险利率 = 股权贴现率的基准）。
 * 收益率上行 -> 成长股估值承压、债券相对股票吸引力上升、企业/地产融资成本抬升；
 * 下行 -> 反之。分界线以美联储圣路易斯联储 FRED DGS10 全史序列（1962 年起，
 * 16,139 个交易日）实测标定为主，机构公开观点为辅。
 */
export const US_10Y_ZONES: readonly ZoneLevel[] = [
  { max: 3.5, label: "宽松/衰退信号", tone: "opportunity", note: "≤ 3.5%：贴现率低位，直接利好成长股估值；但多伴随经济放缓或衰退预期（BofA Hartnett 2025.03：此水平下美债避险需求主导）。参照：2008–2020「低利率时代」10Y 均值仅 2.45%（FRED 实测）" },
  { max: 4.0, label: "中性偏松", tone: "neutral", note: "3.5–4.0%：货币政策偏鸽区间，对股市估值压力有限，历史多数牛市在此环境运行" },
  { max: 4.5, label: "估值甜蜜点", tone: "caution", note: "4.0–4.5%：Morgan Stanley（2025.01）称此区间为美股「甜蜜点」--利率够高支撑金融板块盈利，又未高到压制风险资产估值" },
  { max: 4.75, label: "压力区", tone: "warning", note: "4.5–4.75%：估值压力显现。FRED 实测：2007 年以来仅 6.9% 的交易日 ≥ 4.5%。案例：2024-04-25 触 4.70% 后标普 500 当月回调约 5%" },
  { max: Infinity, label: "危险区", tone: "danger", note: "> 4.75%（5.0% 为硬警戒线）：FRED 实测 2007 年以来仅 0.6% 的交易日 ≥ 5.0%。本轮周期顶 2023-10-19 的 4.98%（17 年新高）出现后标普两周内见底，随后利率回落、股指两个月反弹逾 10%；Evercore ISI（2024.12）：有效突破 5% 将引发「更长更深的调整」" },
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

/** 两融风险区间--主口径：融资余额占流通市值比（%）
 *
 * 绝对余额会随流通市值膨胀而漂移（2015 峰值 2.27万亿 vs 2025 年 3万亿+ 但占比
 * 反而更低），标准风险口径是占流通市值比。分界线非机构观点，而是对沪深交易所
 * 原始数据（东财 RPTA_RZRQ_LSHJ 转引，2010-03-31 两融开闸起全部 3,977 个交易日）
 * 的占比序列做分位数实测标定：P25≈1.96 / P50≈2.20 / P75≈2.36 / P95≈2.98 / P99≈3.92。
 */
export const MARGIN_ZB_ZONES: readonly ZoneLevel[] = [
  { max: 2.0, label: "低杠杆/冰点", tone: "opportunity", note: "≤ 2.0%：全史后 1/4 分位（P25≈1.96%）。2019 年初熊市底实测 1.80% --情绪冰点，往往对应底部区域但市场信心不足" },
  { max: 2.5, label: "常态带", tone: "neutral", note: "2.0–2.5%：2016–2024 各年度的常态运行区间（年区间约 2.0–2.55%，全史中位 2.20%）" },
  { max: 3.0, label: "偏热", tone: "caution", note: "2.5–3.0%：高于常态带，杠杆意愿升温（全史 P95≈2.98%）。2015 牛市主升段与 2026 年（2.50–2.90%）均在此区域" },
  { max: 3.5, label: "过热/关注", tone: "warning", note: "3.0–3.5%：全史仅 4.8% 的交易日 ≥ 3.0%。杠杆加速入场、拥挤度上升，波动放大" },
  { max: Infinity, label: "警戒/过热", tone: "danger", note: "> 3.5%：全史仅 2.5% 的交易日 ≥ 3.5%（P99≈3.92%），且几乎全部集中在 2015 年杠杆牛末段。历史顶 2015-07-03 达 4.70%，随后两个月强平踩踏、上证自 5178 跌至 2850" },
];

/** 两融余额绝对值区间（单位：亿元，辅助口径--受市值膨胀影响，仅供对照） */
export const MARGIN_ZONES: readonly ZoneLevel[] = [
  { max: 15000, label: "低杠杆/情绪谨慎", tone: "caution", note: "< 1.5万亿：市场参与度低，可能处于底部区域但也反映信心不足" },
  { max: 22000, label: "正常区间", tone: "neutral", note: "1.5–2.2万亿：历史常态区间；2015 年峰值 2.27 万亿" },
  { max: 28000, label: "偏高但可控", tone: "warning", note: "2.2–2.8万亿：绝对值偏高，风险以占流通市值比为准（当前约 2.6%）" },
  { max: Infinity, label: "警戒线附近", tone: "danger", note: "> 2.8万亿：绝对值创历史新高，需结合占流通市值比判断（占比 > 3.5% 才进入 2015 式警戒区）" },
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
  margin_rzyezb: [
    { y: 2.0, label: "2.0 冰点(2019底)", color: "#16a34a" },
    { y: 3.0, label: "3.0 正常上限", color: "#6b7280" },
    { y: 3.5, label: "3.5 偏热", color: "#f59e0b" },
    { y: 4.0, label: "4.0 警戒(2015顶)", color: "#dc2626" },
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
  margin_rzyezb: MARGIN_ZB_ZONES,
  margin_rzrqye: MARGIN_ZONES,
  breadth: BREADTH_ZONES,
  pmi: PMI_ZONES,
  cpi: CPI_ZONES,
  ppi: PPI_ZONES,
};

/* ---- 各指标数据来源与分界线出处（抽屉脚注展示）---- */

export const SOURCE_NOTES: Record<string, string> = {
  us_10y:
    "数据来源：东方财富·国债收益率接口（日频），已与美联储圣路易斯联储 FRED DGS10 官方序列交叉验证一致（2026-08-12 双方均为 4.68%）。分界线标定：FRED DGS10 全史序列（1962 年起 16,139 个交易日）实测分位（2007 年来 ≥4.5% 占 6.9%、≥5.0% 占 0.6%）+ 事件锚点（2023-10-19 顶 4.98%、2018-11-08 顶 3.24%、2024-04-25 顶 4.70%）；机构观点（Morgan Stanley 2025.01 / Evercore ISI 2024.12 / BofA Hartnett 2025.03）仅作辅助，非官方标准。",
  cn_10y:
    "数据来源：东方财富·国债收益率接口（中国国债收益率曲线，日频）。分界线为国内券商公开观点归纳（招商证券 2024.12 / 平安理财、开源证券 2025），非官方标准。",
  cn_us_spread_10y:
    "数据来源：中、美 10Y 收益率直接相减（东财接口，日频）。倒挂含义为利差历史规律的归纳（深度倒挂历史上伴随资本外流与人民币贬值压力）。",
  vix:
    "数据来源：CBOE 官方 VIX 指数（yfinance ^VIX 转引，日频）。15/20/30 为 CBOE 指数长期运行区间的经验值。",
  margin_rzyezb:
    "数据来源：东方财富数据中心 RPTA_RZRQ_LSHJ（沪深交易所融资融券原始数据，日频，2010-03-31 两融开闸起）。分界线非机构观点，为对全部 3,977 个交易日占比序列的分位数实测：P25≈1.96 / P50≈2.20 / P95≈2.98 / P99≈3.92，历史极值 2015-07-03 顶 4.70%、2019 年初底 1.80%。",
  margin_rzrqye:
    "数据来源同上（沪深交易所原始数据）。绝对余额受流通市值膨胀影响（2015 峰值 2.27万亿 < 当前 2.68万亿，但风险占比反而更低），仅作辅助口径，风险判断以占流通市值比为准。",
  breadth:
    "数据来源：本系统自算--A 股全成分股收盘价 vs 20/50/200 日均线（东方财富历史K线）。15/50/85 为宽度指标长期统计经验值。",
  pmi: "数据来源：国家统计局月度 PMI（东方财富转引）。50 荣枯线为统计局官方定义。",
  cpi: "数据来源：国家统计局月度 CPI 同比（东方财富转引）。0/3% 为通缩/高通胀经验阈值。",
  ppi: "数据来源：国家统计局月度 PPI 同比（东方财富转引）。0 为通胀/通缩分界。",
};
