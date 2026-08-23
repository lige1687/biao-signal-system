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
      return "#e36b1c"; // amber
    case "warning":
      return "#ea580c"; // orange
    case "danger":
      return "#e33d47"; // red
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

/** VIX 恐慌指数区间
 *
 * 对权益市场而言，VIX 低 = 风险资产环境友好（机会），但需防自满；
 * VIX 高 = 持股风险上升，但尖峰常对应股市阶段性底部（逆向机会）。
 * 因此每个区间都同时标注「机会/风险」含义，不再只写「危险」。
 */
export const VIX_ZONES: readonly ZoneLevel[] = [
  { max: 15, label: "低波动/机会", tone: "opportunity", note: "< 15：机会区间——风险资产估值环境友好；但隐含波动率过低往往伴随自满，需警惕突发冲击（CBOE 历史约 32% 的交易日低于 15）" },
  { max: 20, label: "正常", tone: "neutral", note: "15–20：正常波动区间，接近 CBOE VIX 自 1990 年以来的长期均值（约 19.4–19.7）" },
  { max: 30, label: "风险升温", tone: "caution", note: "20–30：风险升温区——波动升高、风险偏好下降，短期回调概率增加" },
  { max: Infinity, label: "恐慌/逆向机会", tone: "danger", note: "> 30：风险区——市场系统性风险定价偏高，持股压力大；同时也是逆向机会区，历史上 VIX 尖峰常对应股市阶段性底部（CBOE 历史约 8% 的交易日高于 30）" },
];

/** 市场宽度区间（% 站上均线的个股占比）— 行业通用 80/20 极值标准 */
export const BREADTH_ZONES: readonly ZoneLevel[] = [
  { max: 20, label: "超卖/短期底部", tone: "opportunity", note: "< 20%：宽度极低，大概率短期底部；配合 200 日同低可能见反转" },
  { max: 50, label: "中性偏弱", tone: "caution", note: "20–50%：上涨面不足，偏弱" },
  { max: 80, label: "偏热", tone: "neutral", note: "50–80%：上涨面扩大，正常偏强" },
  { max: Infinity, label: "超买/阶段顶部", tone: "danger", note: "> 80%：大概率阶段性顶部" },
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

/**
 * 股权风险溢价 ERP 区间（盈利收益率 − 10Y 国债，单位 %）
 *
 * 机理：ERP 衡量股票相对无风险债券的「额外补偿」。ERP 越高，股票性价比越高
 * （机会）；ERP 转负，说明债券收益率已高于股票盈利收益率，股票相对偏贵（风险）。
 * 中美绝对水平不可直接比（美股利率高、盈利收益率低，A 股反之），故按各自
 * 历史分位实测拆成两套阈值（同 Fed Model 研究惯例），非交易指令。
 *
 * 阈值出处（2026-08 用全史序列实测的分位数）：
 * - A股：沪深300 PE_TTM(乐咕乐股/中证口径, 2005-04 起 5,191 交易日) − 中债10Y，
 *   P20=2.82 / P50=5.08 / P80=6.42；极值 2007-10-17 泡沫顶 -2.46、2014-05-09 大底 8.54。
 * - 美股：S&P500 盈利收益率(multpl/Shiller, 1871 起月度) − 美债10Y，
 *   2006 年以来现代口径 P5≈-0.9 / P20≈0 / P50=1.85 / P80=2.80 / P95=4.40；
 *   全史(1953 起) P5=-2.63 / P50=0.44 / P95=3.79，极值 1992-04-30 -3.57、2011-09-22 5.69。
 */
export const ERP_CN_ZONES: readonly ZoneLevel[] = [
  { max: 2.8, label: "风险/相对债券贵", tone: "danger", note: "< 2.8%（历史 P20 以下）：盈利收益率对无风险利率的补偿垫极薄，股票相对债券明显偏贵（2007 年 6124 点泡沫顶时一度 -2.46）" },
  { max: 5.1, label: "偏低", tone: "caution", note: "2.8–5.1%（P20–P50）：低于历史中位，股债性价比偏股票端谨慎" },
  { max: 6.4, label: "中性", tone: "neutral", note: "5.1–6.4%（P50–P80）：历史常见区间，股债性价比大致均衡" },
  { max: Infinity, label: "机会/相对债券便宜", tone: "opportunity", note: "> 6.4%（历史 P80 以上）：盈利收益率显著高于无风险利率，股票相对债券性价比高（2014-05 大底 8.54、2024 年初均在此区）。注意：2023–2025 连续三年贴此线，择时分辨力有限" },
];

export const ERP_US_ZONES: readonly ZoneLevel[] = [
  { max: 0, label: "风险/债券占优", tone: "danger", note: "≤ 0%：盈利收益率 ≤ 无风险利率，债券相对股票更具吸引力（2025–2026 美股多次转负；1992-04 极端 -3.57）" },
  { max: 1.9, label: "偏低", tone: "caution", note: "0–1.9%（债溢线–P50）：低于 2006 年以来中位，股票相对债券安全垫薄，波动期易回撤" },
  { max: 2.8, label: "中性", tone: "neutral", note: "1.9–2.8%（P50–P80）：历史常见区间，股债性价比大致均衡" },
  { max: Infinity, label: "机会/相对债券便宜", tone: "opportunity", note: "> 2.8%（2006 年以来 P80 以上）：历史多为权益配置舒适区（2011-09 极端 5.69）。注意：2010s 整个十年均值恰好压在此线上，而同期 CAPE 仅 P15——低利率会让本指标长期误亮绿灯" },
];

/**
 * 估值分位对照区间（不受利率水平污染）。
 *
 * 与 ERP_*_ZONES **方向相反**：这里数值高 = 贵 = 风险（红），数值低 = 便宜 = 机会（绿）。
 * 存在理由见 SOURCE_NOTES.cape_us / pe_cn——股债收益差有约七成方差由债券端解释，
 * 单看它会在低利率时代长期误亮绿灯，必须配一个纯估值分位对照。
 *
 * 标定窗口刻意不用全史（理由见各自 note），卡片同时展示标定窗口分位与全史分位。
 */
export const CAPE_US_ZONES: readonly ZoneLevel[] = [
  { max: 12.4, label: "机会/历史级便宜", tone: "opportunity", note: "< 12.4 倍（1950 年以来 P20 以下）：长期回报预期显著高于均值，历史上属世纪级入场区（1982-07 牛市起点 6.6、1932-06 大萧条底 5.6）" },
  { max: 20.2, label: "偏低", tone: "neutral", note: "12.4–20.2 倍（P20–P50）：低于战后中位，长期回报预期偏正（2009-03 金融危机大底 13.3，此时股债收益差反而误报「贵」）" },
  { max: 27.4, label: "偏高", tone: "caution", note: "20.2–27.4 倍（P50–P80）：高于战后中位，长期回报预期被压缩" },
  { max: Infinity, label: "风险/历史级贵", tone: "danger", note: "> 27.4 倍（P80 以上）：长期回报预期显著低于均值（2000-03 互联网顶 43.2、2021-12 流动性顶 38.3）。注意这**不是**卖出信号——2017 年以来美股持续处于本区且大幅上涨" },
];

export const PE_CN_ZONES: readonly ZoneLevel[] = [
  { max: 10.6, label: "机会/历史级便宜", tone: "opportunity", note: "< 10.6 倍（2010 年以来 P20 以下）：历史大底区（2018-12 熊底 10.6、2024-02 底 10.7）" },
  { max: 11.9, label: "偏低", tone: "neutral", note: "10.6–11.9 倍（P20–P50）：低于中位，估值端仍有安全垫" },
  { max: 13.8, label: "偏高", tone: "caution", note: "11.9–13.8 倍（P50–P80）：高于中位，估值端安全垫变薄" },
  { max: Infinity, label: "风险/历史级贵", tone: "danger", note: "> 13.8 倍（P80 以上）：历史顶部区（2015-06 杠杆顶 18.3、2021-02 核心资产顶 17.0、2007-10 泡沫顶 48.2）" },
];

/* ---- 各指标趋势图分界线（与上方区间框架一致）---- */

export const MARKLINES: Record<string, MarkLine[]> = {
  us_10y: [
    { y: 3.5, label: "3.5 宽松", color: "#16a34a" },
    { y: 4.5, label: "4.5 甜蜜点", color: "#e36b1c" },
    { y: 5.0, label: "5.0 危险", color: "#e33d47" },
  ],
  cn_10y: [
    { y: 1.8, label: "1.8 资产荒", color: "#16a34a" },
    { y: 2.2, label: "2.2 合理", color: "#6b7280" },
    { y: 2.5, label: "2.5 收紧", color: "#e36b1c" },
  ],
  cn_us_spread_10y: [
    { y: 0, label: "0 多空分界", color: "#6b7280" },
    { y: -1, label: "-1 深度倒挂", color: "#e33d47" },
  ],
  vix: [
    { y: 15, label: "15 低波动", color: "#16a34a" },
    { y: 20, label: "20 正常", color: "#6b7280" },
    { y: 30, label: "30 恐慌", color: "#e33d47" },
  ],
  margin_rzyezb: [
    { y: 2.0, label: "2.0 冰点(2019底)", color: "#16a34a" },
    { y: 3.0, label: "3.0 正常上限", color: "#6b7280" },
    { y: 3.5, label: "3.5 偏热", color: "#e36b1c" },
    { y: 4.0, label: "4.0 警戒(2015顶)", color: "#e33d47" },
  ],
  margin_rzrqye: [
    { y: 15000, label: "1.5万亿", color: "#e36b1c" },
    { y: 22000, label: "2.2万亿", color: "#6b7280" },
    { y: 28000, label: "2.8万亿", color: "#e33d47" },
  ],
  breadth: [
    { y: 20, label: "20 超卖", color: "#16a34a" },
    { y: 50, label: "50 多空分界", color: "#6b7280" },
    { y: 80, label: "80 超买", color: "#e33d47" },
  ],
  pmi: [{ y: 50, label: "50 荣枯线", color: "#6b7280" }],
  cpi: [{ y: 0, label: "0 通胀/通缩", color: "#6b7280" }],
  ppi: [{ y: 0, label: "0 通胀/通缩", color: "#6b7280" }],
  erp_us: [
    { y: 0, label: "0 债溢线", color: "#e33d47" },
    { y: 1.9, label: "1.9 中位(P50)", color: "#6b7280" },
    { y: 2.8, label: "2.8 机会线(P80)", color: "#16a34a" },
  ],
  erp_cn: [
    { y: 2.8, label: "2.8 风险线(P20)", color: "#e33d47" },
    { y: 5.1, label: "5.1 中位(P50)", color: "#6b7280" },
    { y: 6.4, label: "6.4 机会线(P80)", color: "#16a34a" },
  ],
  // 估值分位对照：方向与 ERP 相反——高 = 贵 = 红。
  cape_us: [
    { y: 12.4, label: "12.4 机会线(P20)", color: "#16a34a" },
    { y: 20.2, label: "20.2 中位(P50)", color: "#6b7280" },
    { y: 27.4, label: "27.4 风险线(P80)", color: "#e33d47" },
  ],
  pe_cn: [
    { y: 10.6, label: "10.6 机会线(P20)", color: "#16a34a" },
    { y: 11.9, label: "11.9 中位(P50)", color: "#6b7280" },
    { y: 13.8, label: "13.8 风险线(P80)", color: "#e33d47" },
  ],
};

/* ---- 宽度多线配置（20/50/200）---- */
export const BREADTH_LINES: LineSeriesConfig[] = [
  { name: "20日", color: "#ea580c" },
  { name: "50日", color: "#2563eb" },
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
  erp_us: ERP_US_ZONES,
  erp_cn: ERP_CN_ZONES,
  cape_us: CAPE_US_ZONES,
  pe_cn: PE_CN_ZONES,
};

/* ---- 趋势图周期选项（利率/资金/ERP 抽屉共用）---- */

/** 默认 3 年；20 年为各序列可得上限（两融 2010 开闸、VIX 1990 起、股债差 2005 起；CAPE 月频 1871 起、沪深300 PE 2005 起，均可覆盖全窗口）。 */
export const RATE_LOOKBACK_OPTIONS: readonly { label: string; days: number }[] = [
  { label: "3年", days: 1095 },
  { label: "5年", days: 1825 },
  { label: "10年", days: 3650 },
  { label: "20年", days: 7300 },
];

/* ---- 叠图专用分界线：同样的阈值，但按「对股市意味着什么」措辞 ---- */

/**
 * 长周期叠图右轴的压力位 / 机会位。
 * 阈值与 MARKLINES 完全一致（同一套标定，见 SOURCE_NOTES），区别只在标签：
 * 抽屉里看的是利率自身处在什么水平，叠图里看的是它对股指构成压力还是机会
 * ——利率高 = 贴现率高 = 杀估值 = 压力位；利率低 = 宽松 = 机会位。
 */
export const OVERLAY_MARKLINES: Record<string, MarkLine[]> = {
  us_10y: [
    { y: 3.5, label: "3.5% 机会位·宽松", color: "#16a34a" },
    { y: 4.5, label: "4.5% 压力位·估值承压", color: "#e36b1c" },
    { y: 5.0, label: "5.0% 强压力·杀估值", color: "#e33d47" },
  ],
  cn_10y: [
    { y: 1.8, label: "1.8% 机会位·资产荒", color: "#16a34a" },
    { y: 2.2, label: "2.2% 合理中枢", color: "#6b7280" },
    { y: 2.5, label: "2.5% 压力位·资金收紧", color: "#e36b1c" },
  ],
  margin_rzyezb: [
    { y: 2.0, label: "2.0% 机会位·杠杆冰点", color: "#16a34a" },
    { y: 3.0, label: "3.0% 常态上限", color: "#6b7280" },
    { y: 3.5, label: "3.5% 压力位·偏热", color: "#e36b1c" },
    { y: 4.0, label: "4.0% 强压力·2015 顶", color: "#e33d47" },
  ],
  // 叠图里按「对股市意味着什么」措辞——股债差低 = 股票相对债券贵（红），高 = 相对便宜（绿）。
  erp_cn: [
    { y: 2.8, label: "股债差 2.8 风险线", color: "#e33d47" },
    { y: 5.1, label: "股债差 5.1 中位", color: "#6b7280" },
    { y: 6.4, label: "股债差 6.4 机会线", color: "#16a34a" },
  ],
  erp_us: [
    { y: 0, label: "股债差 0 债券占优", color: "#e33d47" },
    { y: 1.9, label: "股债差 1.9 中位", color: "#6b7280" },
    { y: 2.8, label: "股债差 2.8 机会线", color: "#16a34a" },
  ],
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
    "数据：CBOE Volatility Index（^VIX），由芝加哥期权交易所（CBOE）编制，via Yahoo Finance v8 图表 API（日频）。VIX 计算方法见 CBOE VIX White Paper（CBOE, 2003；Carr & Wu, 2006, The Journal of Derivatives）。分界线 15/20/30 为市场惯例阈值，基于 CBOE 官方日频历史（1990-01-02 起）标定：20 大致对应长期均值约 19.4–19.7；30 接近历史 90 分位（极端恐慌，约 8% 交易日高于 30）；15 以下为低波动/自满区（约 32% 交易日低于 15）。本页统计口径与 CBOE 官方日频序列一致。区间解读为研究归纳，非交易指令。",
  margin_rzyezb:
    "数据来源：东方财富数据中心 RPTA_RZRQ_LSHJ（沪深交易所融资融券原始数据，日频，2010-03-31 两融开闸起）。分界线非机构观点，为对全部 3,977 个交易日占比序列的分位数实测：P25≈1.96 / P50≈2.20 / P95≈2.98 / P99≈3.92，历史极值 2015-07-03 顶 4.70%、2019 年初底 1.80%。",
  margin_rzrqye:
    "数据来源同上（沪深交易所原始数据）。绝对余额受流通市值膨胀影响（2015 峰值 2.27万亿 < 当前 2.68万亿，但风险占比反而更低），仅作辅助口径，风险判断以占流通市值比为准。",
  breadth:
    "数据来源：本系统自算——A 股全成分股收盘价 vs 20/50/200 日均线（东方财富历史K线）。极值阈值采用行业通用标准：80% 超买 / 20% 超卖 / 50% 多空分界（TradingView 宽度脚本、marketinout %Above50MA、thetrading.tools 等 quant 框架；华泰证券《A股择时之技术面指标测试》(2021) 亦建议对 A 股采用标准/默认参数）。",
  pmi: "数据来源：国家统计局月度 PMI（东方财富转引）。50 荣枯线为统计局官方定义。",
  cpi: "数据来源：国家统计局月度 CPI 同比（东方财富转引）。0/3% 为通缩/高通胀经验阈值。",
  ppi: "数据来源：国家统计局月度 PPI 同比（东方财富转引）。0 为通胀/通缩分界。",
  erp_us:
    "股债收益差（Fed Model 口径）= S&P500 盈利收益率(1/PE_TTM×100) − 美债 10Y。\n\n" +
    "⚠️ 口径说明：这是 ERP（股权风险溢价）的粗略代理，不是严格 ERP。ERP 本身是不可观测的预期超额回报，估计方法有四类：① 历史已实现超额收益 ② 隐含 ERP（Damodaran 用贴现模型反解贴现率，美股典型 4%–6%）③ 调查法 ④ 本指标 E/P − 名义10Y。本指标是四者中最粗的一种，且用的是 TTM 滚动盈利而非前瞻盈利，与 ① ② ③ 的数值不可直接比。另注：「Fed Model」这个名字是 Ed Yardeni 起的，源自美联储 1997 年 Humphrey-Hawkins 报告里的一张图，美联储从未正式采纳过——方法论被广泛使用，但没有官方背书。\n\n" +
    "【适用】中短期股债相对吸引力扫描、战术资产配置——回答「现在买股票相对买债券划不划算」。\n" +
    "【不适用】判断股票绝对贵贱；长期回报预测；盈利塌陷期。\n\n" +
    "本系统实测局限（multpl 月度全史 1872–2026，1,851 个月）：\n" +
    "① 利率主导：corr(本指标, 名义10Y) = −0.54，1990 年后 −0.83（R²≈0.69）——约七成方差由债券端解释，它主要是个债券指标。与当期 CPI 相关性仅 +0.10，说明错配是通过名义利率水平传导，不是通过当期通胀。\n" +
    "② 同读数反真相：1980s 均值 −1.61（看着贵）而 CAPE 11.5 = P84 极便宜；1990s 均值 −1.79（几乎同一读数）而 CAPE 25.3 = P18 极贵。\n" +
    "③ 低利率时代长期误亮绿灯：2010s 均值 +2.80，恰好压在本图机会线上，而同期 CAPE 仅 P15。\n" +
    "④ 盈利塌陷期失真：2009-03 金融危机大底读数 −1.91（P7）误报「贵」——TTM 盈利崩塌快于股价。\n" +
    "⑤ 长期预测力弱：与未来 10 年实际回报相关 +0.15，而 CAPE 盈利收益率为 +0.34（约 2.2 倍）。注：10 年窗口重叠、未含分红，属方向性结论而非显著性检验。\n" +
    "⑥ 事件锚点 7/10：✓ 2000-03 顶 −2.73(P3)、2020-03 底 +3.52(P65)、1932-06 底 +7.16(P92)；✗ 1982-07 牛市起点 −1.18(P12)、2009-03 大底(P7)、2021-12 顶 +2.76(P51)。\n" +
    "→ 请与「美股 CAPE 估值分位」卡片配对看：两者同时到极值才是强信号；打架时说明「股票贵但债券更贵」，那是配置结论，不是择时结论。\n\n" +
    "数据：盈利收益率现值取 multpl.com 主页（日频），历史取其月度全史表（1,863 期，1871 年起，EPS 溯源自 Robert Shiller 耶鲁数据）；10Y 国债 via 东方财富（已与美联储 FRED DGS10 交叉验证）。分界线为本系统对 2006 年以来序列的实测分位（P50=1.85 / P80=2.80；全史 P50=0.44 / P95=3.79），非任何官方公布的标准线。月度表滞后主页现值数月，图末端与卡片可能有小差。区间解读为研究归纳，非交易指令。",
  erp_cn:
    "股债收益差（Fed Model 口径）= 沪深300 盈利收益率(1/PE_TTM×100) − 中债 10Y。A 股研报通称「股权风险溢价／股债收益差」，中金策略、兴业金工等均以历史分位刻画股债性价比。\n\n" +
    "⚠️ 口径说明：同美股卡片——这是 ERP 的粗略代理而非严格 ERP，用 TTM 滚动盈利，与 Damodaran 隐含 ERP 不可直接比；「Fed Model」无美联储官方背书。\n\n" +
    "【适用】A股股债相对吸引力、战术配置切换。\n" +
    "【不适用】判断股票绝对贵贱；利率单边趋势期的择时；盈利塌陷期。\n\n" +
    "本系统实测（乐咕乐股沪深300 PE_TTM 全史 2005-04-08 起 5,191 个交易日 × 东财中债 10Y）：\n" +
    "① 与美股不同，A 股这个指标主要由股票端驱动：corr(本指标, 盈利收益率) = +0.96，corr(本指标, 中债10Y) = −0.43。因为中债 10Y 区间窄（1.7–4.2），而沪深300 PE_TTM 摆动 8.7–39.9，股票端噪音压倒债券端。所以「通胀错配」这条批评在 A 股比在美股轻得多。\n" +
    "② 但利率下行造成的假机会真实存在：2022→2025，PE_TTM 从 11.4 升到 12.5（股票变贵了）、盈利收益率从 8.83 降到 8.05，而本指标反而从 6.07 升到 6.31（更「机会」）——纯粹因为中债 10Y 塌了 1.03 个百分点。\n" +
    "③ 分位随窗口大幅漂移：2012 年前 P20=−0.06 / P50=2.45 / P80=4.18；全史 P20=2.82 / P50=5.08 / P80=6.42；近 7 年 P20=4.93 / P50=5.76 / P80=6.56。本图分界线用全史，与最长 20 年窗口自洽，但往 2012 年前外推会误导。\n" +
    "④ 择时分辨力有限：2023/2024/2025 年均值分别 6.39 / 6.64 / 6.31，连续三年贴着或压在机会线（6.42）上——方向上它说 A 股便宜（事后看不算错），但这三年它几乎不给区分度。\n" +
    "⑤ 事件锚点全部正确检出：2007-10 大顶 −2.40(P0.1)、2015-06 杠杆顶 +1.85(P12.8) 均在风险线下；2014-05 大底 +8.54(P99.9)、2018-12 熊底 +6.68(P85.6)、2024-02 底 +7.43(P95.9) 均在机会线上。\n" +
    "→ 请与「沪深300 PE_TTM 估值分位」卡片配对看，理由同美股卡片。\n\n" +
    "数据：PE_TTM 现值链 东财 dcfm → 乐咕乐股（via akshare）→ yfinance 兜底；历史取乐咕乐股滚动市盈率全史（与中证指数有限公司官方编制口径一致）；10Y 国债 via 东方财富（中债估值口径）。分界线为本系统实测分位，非官方公布标准线。区间解读为研究归纳，非交易指令。",
  cape_us:
    "CAPE（Shiller PE，周期调整市盈率）= S&P500 实际价格 ÷ 过去 10 年通胀调整后实际盈利均值。方法论出处：2013 年诺贝尔经济学奖得主 Robert Shiller（耶鲁）；数据溯源自其 Irrational Exuberance 公开序列，1871 年起。\n\n" +
    "为什么加这个指标：股债收益差（Fed Model 口径）在 1990 年后与名义 10Y 的相关系数实测 −0.83，约七成方差由债券端解释，在低利率时代会长期误亮绿灯。CAPE 用 10 年平均实际盈利做分母，既不含利率项、又避开盈利拐点处的分母失真，是股债收益差的对照而非替代。\n\n" +
    "【适用】10 年级别长期回报预期、判断股票绝对贵贱、校正股债收益差的利率污染。\n" +
    "【不适用】择时和短期方向——CAPE 高位可持续多年：2017 年以来美股持续处在本图风险区，期间仍大幅上涨，它刻画的是长期回报预期下移，不是卖出信号。也不适合跨市场直接比较（会计口径、行业结构、回购比例不同）。\n\n" +
    "本系统实测（multpl 月度全史 1871-02 起 1,867 期）：\n" +
    "① 分界线取 1950 年以来分位（920 个月）：P20=12.4 / P50=20.2 / P80=27.4。刻意不用全史（P20=11.2 / P50=16.1 / P80=22.4）——1871–1949 的会计与指数编制口径不可比；也不用 1990 年后（P20=21.0 / P50=26.4 / P80=33.0）——样本仅 36 年且全落在低利率＋回购时代，会把风险门槛抬到失去警示意义。分位是取样窗口的函数，卡片同时展示标定窗口分位与全史分位就是为了让这一点可见。\n" +
    "② 事件锚点 3/3：2000-03 互联网顶 43.2(P100)、2009-03 金融危机大底 13.3(P22)、2021-12 流动性顶 38.3(P96)。其中 2009-03 正是股债收益差失手的地方（那里它报 P7「贵」）——这是两个指标配对使用最直接的理由。\n" +
    "③ 长期预测力：CAPE 盈利收益率与未来 10 年实际回报相关 +0.34，股债收益差为 +0.15。注：10 年窗口重叠、未含分红，方向性结论非显著性检验。\n\n" +
    "数据：multpl.com 月度表（EPS/CPI 溯源自 Robert Shiller 耶鲁公开数据）。月频，故图上点数少于日频序列。区间解读为研究归纳，非交易指令。",
  pe_cn:
    "沪深300 PE_TTM 估值分位 = 滚动市盈率在历史分布中的位置（越高越贵）。\n\n" +
    "为什么加这个指标：A 股股债收益差虽主要由股票端驱动（相关 +0.96），但中债 10Y 单边下行会推高它——2022→2025 沪深300 PE 从 11.4 升到 12.5（更贵了），股债收益差却从 6.07 升到 6.31（更「机会」）。看 PE 自身分位可以直接识别这种假机会。\n\n" +
    "【适用】A 股绝对估值贵贱、校正股债收益差被利率下行推高的假机会。\n" +
    "【不适用】跨市场比较（沪深300 金融权重高，行业结构与标普500 差异大）；盈利拐点处——PE_TTM 同样有滚动盈利滞后问题，2008-10 熊底 PE=13.9（全史 P68，看着「贵」）就是因为分母还是 2007 年的高盈利。美股用 CAPE 的 10 年均值绕开了这一点，A 股缺可比的 10 年实际盈利序列，故无法直接照搬——这是本指标已知的结构性短板。\n\n" +
    "本系统实测（乐咕乐股全史 2005-04-08 起 5,191 个交易日）：\n" +
    "① 分界线取 2010 年以来分位（4,037 日）：P20=10.6 / P50=11.9 / P80=13.8。不用全史（P20=11.0 / P50=12.6 / P80=15.5、P95=34.4）——股权分置改革前后小流通盘时代 PE 口径不可比，全史 P95 几乎全部由 2007 泡沫单独贡献，用它标定会把「不贵」门槛抬到失去分辨力。\n" +
    "② 事件锚点 4/4：2015-06 杠杆顶 18.3(P98)、2018-12 熊底 10.6(P19)、2021-02 核心资产顶 17.0(P97)、2024-02 底 10.7(P22)。\n\n" +
    "数据：乐咕乐股（via akshare），与中证指数有限公司官方编制口径一致。区间解读为研究归纳，非交易指令。",
};

/* ---- 叠图条件高亮：6 条宽度规则的多选触发 ---- */

/** 规则的元数据：chip 展示 + 高亮色带。阈值不在此处写死，由 evalBreadthRule() 按市场切换。 */
export interface BreadthHighlightRuleMeta {
  key: string;
  /** chip 短标签（≤ 10 字） */
  short: string;
  /** tooltip / 图例全名 */
  full: string;
  /** 色带主色 */
  color: string;
  /** 色带不透明度（0–1） */
  opacity: number;
  /** 类目：stage=阶段性、reversal=反转、base=底色 */
  kind: "stage" | "reversal" | "base";
}

/**
 * 6 条规则的 chip 元数据。
 * 文案与 MarketBreadthModal 第 142-168 行规则一一对应；阈值口径已写明
 * （A股 80/20 与 MarketBreadthModal + symbols.py:_breadth_alerts() 一致；
 *  美股 85/15 与 market_context/classifier.py:_detect_extreme_events 一致）。
 */
export const BREADTH_HIGHLIGHT_RULES: readonly BreadthHighlightRuleMeta[] = [
  { key: "stage_top",       short: "B50 阶段顶",    full: "B50 ≥ 80%(A股) / ≥ 85%(美股) 阶段性顶部预警——大概率短期高点",     color: "#e33d47", opacity: 0.16, kind: "stage" },
  { key: "stage_bottom",    short: "B50 阶段底",    full: "B50 ≤ 20%(A股) / ≤ 15%(美股) 短期底部预警——大概率短期低点",       color: "#16a34a", opacity: 0.16, kind: "stage" },
  { key: "reversal_top",    short: "B50+B200 反转顶", full: "B50 与 B200 同时 ≥ 80%(A股) / ≥ 85%(美股) 反转顶部信号——两周期共振极热", color: "#991b1b", opacity: 0.22, kind: "reversal" },
  { key: "reversal_bottom", short: "B50+B200 反转底", full: "B50 与 B200 同时 ≤ 20%(A股) / ≤ 15%(美股) 反转底部信号——两周期共振极冷", color: "#166534", opacity: 0.22, kind: "reversal" },
  { key: "bull_base",       short: "B200 牛市底色", full: "B200 > 50% 牛市底色——长期趋势偏多",                              color: "#16a34a", opacity: 0.08, kind: "base" },
  { key: "bear_base",       short: "B200 熊市底色", full: "B200 < 50% 熊市底色——长期趋势偏空",                              color: "#e33d47", opacity: 0.08, kind: "base" },
];

/** 支持的市场标签 */
export type BreadthMarket = "CN" | "US";

/**
 * 评估某天某条规则是否触发。
 * 阈值口径：A 股 80/20（与 MarketBreadthModal 第 142-168 行 + symbols.py:_breadth_alerts() 一致），
 *           美股 85/15（与 market_context/classifier.py:_detect_extreme_events 一致），
 *           牛/熊底色 50 在两市场通用。
 * b20 当前未参与任何规则，但保留位置以便未来扩展「三线共振」类信号。
 */
export function evalBreadthRule(
  ruleKey: string,
  market: BreadthMarket,
  _b20: number | null,
  b50: number | null,
  b200: number | null,
  thresholds?: { hot: number; cold: number },
): boolean {
  const hot = thresholds?.hot ?? (market === "CN" ? 80 : 85);
  const cold = thresholds?.cold ?? (market === "CN" ? 20 : 15);
  switch (ruleKey) {
    case "stage_top":
      return b50 != null && b50 >= hot;
    case "stage_bottom":
      return b50 != null && b50 <= cold;
    case "reversal_top":
      return b50 != null && b200 != null && b50 >= hot && b200 >= hot;
    case "reversal_bottom":
      return b50 != null && b200 != null && b50 <= cold && b200 <= cold;
    case "bull_base":
      return b200 != null && b200 > 50;
    case "bear_base":
      return b200 != null && b200 < 50;
    default:
      return false;
  }
}

/** 单条高亮色带（喂给 OverlayChart 的 markArea）。 */
export interface HighlightBand {
  key: string;
  label: string;
  color: string;
  opacity: number;
  /** 连续区间的 [startDate, endDate]（同一天 start==end 也是合法单点） */
  ranges: Array<[string, string]>;
}

/** 把布尔序列压成连续区间的 [startIdx, endIdx]，端点都包含。 */
function condenseRanges(flags: boolean[]): Array<[number, number]> {
  const out: Array<[number, number]> = [];
  let start: number | null = null;
  for (let i = 0; i <= flags.length; i++) {
    const isOn = i < flags.length && flags[i];
    if (isOn && start === null) start = i;
    if (start !== null && !isOn) {
      out.push([start, i - 1]);
      start = null;
    }
  }
  return out;
}

/**
 * 把当前激活的规则集展开为 HighlightBand[]（仅返回有命中区间的）。
 * 区间覆盖宽度格（0–100%），由 OverlayChart 渲染为 markArea。
 * 不在 BREADTH_HIGHLIGHT_RULES 内的 key 静默跳过，避免脏数据炸图。
 */
export function computeHighlightBands(
  activeKeys: ReadonlySet<string>,
  market: BreadthMarket,
  dates: readonly string[],
  v20: readonly (number | null)[],
  v50: readonly (number | null)[],
  v200: readonly (number | null)[],
  thresholds?: { hot: number; cold: number },
): HighlightBand[] {
  if (activeKeys.size === 0 || dates.length === 0) return [];
  const bands: HighlightBand[] = [];
  for (const meta of BREADTH_HIGHLIGHT_RULES) {
    if (!activeKeys.has(meta.key)) continue;
    const flags: boolean[] = new Array(dates.length);
    for (let i = 0; i < dates.length; i++) {
      flags[i] = evalBreadthRule(meta.key, market, v20[i], v50[i], v200[i], thresholds);
    }
    const ranges: Array<[string, string]> = [];
    for (const [s, e] of condenseRanges(flags)) {
      const sd = dates[s];
      const ed = dates[e];
      if (sd != null && ed != null) ranges.push([sd, ed]);
    }
    if (ranges.length === 0) continue;
    bands.push({
      key: meta.key,
      label: meta.full,
      color: meta.color,
      opacity: meta.opacity,
      ranges,
    });
  }
  return bands;
}
