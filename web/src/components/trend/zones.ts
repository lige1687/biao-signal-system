/** Shared display metadata for observation charts.
 * A source series and a historical frequency do not validate a trading threshold.
 * Only arithmetic or source-defined reference lines remain visible by default.
 */
export type Tone = "opportunity" | "neutral" | "caution" | "warning" | "danger";
export interface ZoneLevel { max: number; label: string; tone: Tone; note: string }
export interface MarkLine { y: number; label: string; color: string }
export interface LineSeriesConfig { name: string; color: string }

export function zoneToneColor(tone: Tone): string {
  switch (tone) {
    case "opportunity": return "#16a34a";
    case "caution": return "#e36b1c";
    case "warning": return "#ea580c";
    case "danger": return "#e33d47";
    default: return "#6b7280";
  }
}

export function findZone(value: number | null, zones: readonly ZoneLevel[]): ZoneLevel {
  if (value === null || !Number.isFinite(value) || zones.length === 0) {
    return { max: Infinity, label: "暂无有效读数", tone: "neutral", note: "以原始资料日期和单位为准。" };
  }
  return zones.find((zone) => value <= zone.max) ?? zones[zones.length - 1];
}

const neutral = (note: string): readonly ZoneLevel[] => [
  { max: Infinity, label: "观察读数", tone: "neutral", note },
];
const sign = (negative: string, zero: string, positive: string): readonly ZoneLevel[] => [
  { max: -Number.MIN_VALUE, label: negative, tone: "neutral", note: "数值小于 0；只描述原指标方向。" },
  { max: 0, label: zero, tone: "neutral", note: "数值等于 0；不据此推断市场顶底。" },
  { max: Infinity, label: positive, tone: "neutral", note: "数值大于 0；只描述原指标方向。" },
];

/** No rate level here has qualified evidence as an equity opportunity or pressure line. */
export const US_10Y_ZONES = neutral("美国10年国债收益率水平；变化会影响贴现背景，但固定点位未经交易用途验证。");
export const CN_10Y_ZONES = neutral("中国10年国债收益率水平；固定点位未经交易用途验证。");
export const CN_US_SPREAD_ZONES: readonly ZoneLevel[] = sign("中债收益率低于美债", "中美10年收益率相等", "中债收益率高于美债");
export const MARGIN_ZB_ZONES = neutral("融资余额占流通市值比；历史位置不自动构成底部、顶部或风险界线。");
export const MARGIN_ZONES = neutral("两融余额绝对值随市场规模变化；不设固定机会或警戒线。");
export const VIX_ZONES = neutral("VIX 反映标普500期权隐含的约30天预期波动幅度，不表示方向或固定买卖区间。");
export const BREADTH_ZONES = neutral("宽度为站上均线的股票比例；高低只描述参与范围，未验证顶底阈值。");
export const PMI_ZONES: readonly ZoneLevel[] = [
  // Largest representable double below 50; Number.EPSILON alone rounds back to 50 here.
  { max: 49.99999999999999, label: "PMI低于50", tone: "neutral", note: "制造业调查相对上月呈收缩方向；50为来源定义的分界。" },
  { max: 50, label: "PMI等于50", tone: "neutral", note: "制造业调查相对上月大致持平。" },
  { max: Infinity, label: "PMI高于50", tone: "neutral", note: "制造业调查相对上月呈扩张方向；不表示股票收益方向。" },
];
export const CPI_ZONES = sign("CPI同比下降", "CPI同比持平", "CPI同比上升");
export const PPI_ZONES = sign("PPI同比下降", "PPI同比持平", "PPI同比上升");
export const ICWA_ZONES = neutral("美国初请失业金四周均值；绝对人数随人口与制度变化，不设固定衰退线。");
export const CCWA_ZONES = neutral("美国续请失业金人数；绝对人数不设固定市场阈值。");
export const PAYEMS_YOY_ZONES = sign("非农就业人数同比减少", "非农就业人数同比持平", "非农就业人数同比增加");
export const HSALES_ZONES = neutral("美国新屋销售折年率；只描述成交规模，不设固定市场阈值。");
export const CSHPI_YOY_ZONES = sign("房价指数同比下降", "房价指数同比持平", "房价指数同比上升");
export const ALTSA_ZONES = neutral("美国汽车销量折年率；只描述销售规模，不设固定市场阈值。");
export const WEI_ZONES = sign("WEI低于零", "WEI等于零", "WEI高于零");
export const US_PPI_ZONES = sign("美国PPI同比下降", "美国PPI同比持平", "美国PPI同比上升");
export const US_CPI_ZONES = sign("美国CPI同比下降", "美国CPI同比持平", "美国CPI同比上升");
export const DGORDER_YOY_ZONES = sign("耐用品订单同比减少", "耐用品订单同比持平", "耐用品订单同比增加");
export const HY_OAS_ZONES = neutral("美国高收益债相对国债的信用利差；无已验证的固定交易或危机点位。");
export const ERP_CN_ZONES = sign("A股盈利收益率低于10年国债收益率", "A股盈利收益率等于10年国债收益率", "A股盈利收益率高于10年国债收益率");
export const ERP_US_ZONES = sign("美股盈利收益率低于10年国债收益率", "美股盈利收益率等于10年国债收益率", "美股盈利收益率高于10年国债收益率");
export const CAPE_US_ZONES = neutral("Shiller CAPE 是历史估值背景；固定倍数和历史分位没有验证为大盘顶底线。");
export const PE_CN_ZONES = neutral("沪深300 PE_TTM 是该指数估值背景；固定倍数没有验证为大盘顶底线。");

const zeroLine = (label: string): MarkLine[] => [{ y: 0, label, color: "#6b7280" }];
/** Visible lines are structural definitions, not action thresholds. */
export const MARKLINES: Record<string, MarkLine[]> = {
  us_10y: [], cn_10y: [], cn_us_spread_10y: zeroLine("0 收益率相等"),
  vix: [], margin_rzyezb: [], margin_rzrqye: [],
  breadth: [{ y: 50, label: "50% 半数上方", color: "#6b7280" }],
  pmi: [{ y: 50, label: "50 扩张/收缩分界", color: "#6b7280" }],
  cpi: zeroLine("0 同比持平"), ppi: zeroLine("0 同比持平"),
  icwa: [], ccwa: [], payems_yoy: zeroLine("0 同比持平"), hsales: [],
  cshpi_yoy: zeroLine("0 同比持平"), altsa: [], wei: zeroLine("0 周经济指数分界"),
  ppiaco_yoy: zeroLine("0 同比持平"), cpiaucsl_yoy: zeroLine("0 同比持平"),
  dgorder_yoy: zeroLine("0 同比持平"), hy_oas: [],
  erp_us: zeroLine("0 两端收益率相等"), erp_cn: zeroLine("0 两端收益率相等"),
  cape_us: [], pe_cn: [],
};

export const BREADTH_LINES: LineSeriesConfig[] = [
  { name: "20日", color: "#ea580c" },
  { name: "50日", color: "#2563eb" },
  { name: "200日", color: "#7c3aed" },
];

export const ZONES: Record<string, readonly ZoneLevel[]> = {
  us_10y: US_10Y_ZONES, cn_10y: CN_10Y_ZONES, cn_us_spread_10y: CN_US_SPREAD_ZONES,
  vix: VIX_ZONES, margin_rzyezb: MARGIN_ZB_ZONES, margin_rzrqye: MARGIN_ZONES,
  breadth: BREADTH_ZONES, pmi: PMI_ZONES, cpi: CPI_ZONES, ppi: PPI_ZONES,
  erp_us: ERP_US_ZONES, erp_cn: ERP_CN_ZONES, cape_us: CAPE_US_ZONES, pe_cn: PE_CN_ZONES,
  icwa: ICWA_ZONES, ccwa: CCWA_ZONES, payems_yoy: PAYEMS_YOY_ZONES,
  hsales: HSALES_ZONES, cshpi_yoy: CSHPI_YOY_ZONES, altsa: ALTSA_ZONES,
  wei: WEI_ZONES, ppiaco_yoy: US_PPI_ZONES, cpiaucsl_yoy: US_CPI_ZONES,
  dgorder_yoy: DGORDER_YOY_ZONES, hy_oas: HY_OAS_ZONES,
};

export const RATE_LOOKBACK_OPTIONS: readonly { label: string; days: number }[] = [
  { label: "3年", days: 1095 }, { label: "5年", days: 1825 },
  { label: "10年", days: 3650 }, { label: "20年", days: 7300 },
];

/** Overlay callers retain the same keys; unsupported rate and leverage markers are gone. */
export const OVERLAY_MARKLINES: Record<string, MarkLine[]> = {
  us_10y: [], cn_10y: [], margin_rzyezb: [],
  erp_cn: zeroLine("股债差 0 两端相等"), erp_us: zeroLine("股债差 0 两端相等"),
};

/** State the source and the actual descriptive purpose; source authority is not efficacy evidence. */
export const SOURCE_NOTES: Record<string, string> = {
  us_10y: "美国10年国债收益率，东方财富接口；本页作利率与贴现背景观察，固定收益率点位未经股票交易用途验证。",
  cn_10y: "中国10年国债收益率，东方财富接口；本页作利率背景观察，固定点位未经股票交易用途验证。",
  cn_us_spread_10y: "中国减美国10年国债收益率；0仅表示两端收益率相等，不是汇率或股票方向分界。",
  vix: "Cboe VIX 经 Yahoo 转发；Cboe 定义其为标普500期权隐含的约30天预期波动幅度。12/20等示例仅说明波动量级；15/20/30未验证为方向、顶底或交易界线。",
  margin_rzyezb: "东方财富转引沪深交易所两融历史，融资余额占流通市值比；历史分位仅说明分布位置，未验证固定顶底点位。",
  margin_rzrqye: "东方财富转引沪深交易所两融合计余额；绝对金额受市场规模影响，不设固定风险线。",
  breadth: "站上20/50/200日均线的股票比例；50%只表示半数上方。A股80/20、美股85/15为本系统已有数值查询条件，未验证为顶底预测阈值。",
  pmi: "国家统计局制造业PMI，经东方财富转引；国家统计局说明 https://www.stats.gov.cn/zs/tjws/tjzb/202301/t20230101_1903972.html 将50%定义为扩张、收缩分界，不是股票方向线。",
  cpi: "国家统计局CPI同比，经东方财富转引；0只表示同比价格水平持平。",
  ppi: "国家统计局PPI同比，经东方财富转引；0只表示同比价格水平持平。",
  icwa: "美国劳工部初请失业金人数，FRED转发并计算四周均值；绝对人数不设固定衰退或股市交易阈值。",
  ccwa: "美国劳工部续请失业金人数，FRED转发；人口和制度变化使绝对水平难直接横比。",
  payems_yoy: "美国劳工部非农就业人数PAYEMS，FRED转发并计算同比；0只表示就业人数同比持平。",
  hsales: "美国普查局新屋销售HSN1F，FRED转发，单位为千套折年率；不设固定市场阈值。",
  cshpi_yoy: "S&P/Case-Shiller美国全国房价指数，FRED转发并计算同比；0只表示同比持平。",
  altsa: "美联储G.17汽车销量TOTALSA，FRED转发，百万辆折年率；不设固定市场阈值。",
  wei: "纽约联储WEI周经济指数，FRED转发；0是该经济活动代理的增长、收缩分界，不是GDP公布值或股票信号。",
  ppiaco_yoy: "美国劳工部最终需求PPI PPIFIS，FRED转发并计算同比；0只表示同比持平。",
  cpiaucsl_yoy: "美国劳工部城市CPI CPIAUCSL，FRED转发并计算同比；联储2%长期目标针对PCE而非本序列。",
  dgorder_yoy: "美国普查局耐用品订单DGORDER，FRED转发并计算同比；不是ISM PMI，0只表示订单同比持平。",
  hy_oas: "ICE BofA美国高收益债期权调整利差BAMLH0A0HYM2，FRED转发；利差是信用风险补偿，不是违约率；无已验证固定交易线。",
  erp_us: "美股盈利收益率减美国10年国债收益率，Fed Model式粗略股债差；0仅表示两端相等，并非可观测预期超额回报或交易界线。",
  erp_cn: "沪深300盈利收益率减中国10年国债收益率，Fed Model式粗略股债差；0仅表示两端相等，历史分位未验证为顶底界线。",
  cape_us: "multpl.com Shiller PE月度表，盈利数据溯源Shiller；用于美国长期估值背景，月初日期为所属月，未验证固定倍数为市场顶底。",
  pe_cn: "乐咕乐股沪深300滚动市盈率，经akshare读取；用于该指数自身估值背景，未验证固定倍数为市场顶底。",
};

/** Existing internal keys are retained for stored selections and callers; labels describe numeric facts only. */
export interface BreadthHighlightRuleMeta {
  key: string; short: string; full: string; color: string; opacity: number;
  kind: "stage" | "reversal" | "base";
}
export const BREADTH_HIGHLIGHT_RULES: readonly BreadthHighlightRuleMeta[] = [
  { key: "stage_top", short: "B50较高", full: "B50 ≥ A股80%／美股85%：现有数值查询，未验证后续价格走势。", color: "#9b744d", opacity: 0.14, kind: "stage" },
  { key: "stage_bottom", short: "B50较低", full: "B50 ≤ A股20%／美股15%：现有数值查询，未验证后续价格走势。", color: "#527ca2", opacity: 0.14, kind: "stage" },
  { key: "reversal_top", short: "B50+B200较高", full: "B50与B200同时 ≥ A股80%／美股85%：两周期参与比例查询，未验证后续价格走势。", color: "#8d6f60", opacity: 0.18, kind: "reversal" },
  { key: "reversal_bottom", short: "B50+B200较低", full: "B50与B200同时 ≤ A股20%／美股15%：两周期参与比例查询，未验证后续价格走势。", color: "#506f91", opacity: 0.18, kind: "reversal" },
  { key: "bull_base", short: "B200>50%", full: "B200 > 50%：半数以上股票站上200日均线。", color: "#62849a", opacity: 0.07, kind: "base" },
  { key: "bear_base", short: "B200<50%", full: "B200 < 50%：半数以上股票未站上200日均线。", color: "#a08a75", opacity: 0.07, kind: "base" },
];
export type BreadthMarket = "CN" | "US";

/** Preserve the existing numerical queries; this is not a validated predictive rule. */
export function evalBreadthRule(
  ruleKey: string, market: BreadthMarket, _b20: number | null,
  b50: number | null, b200: number | null, thresholds?: { hot: number; cold: number },
): boolean {
  const hot = thresholds?.hot ?? (market === "CN" ? 80 : 85);
  const cold = thresholds?.cold ?? (market === "CN" ? 20 : 15);
  switch (ruleKey) {
    case "stage_top": return b50 != null && b50 >= hot;
    case "stage_bottom": return b50 != null && b50 <= cold;
    case "reversal_top": return b50 != null && b200 != null && b50 >= hot && b200 >= hot;
    case "reversal_bottom": return b50 != null && b200 != null && b50 <= cold && b200 <= cold;
    case "bull_base": return b200 != null && b200 > 50;
    case "bear_base": return b200 != null && b200 < 50;
    default: return false;
  }
}

export interface HighlightBand {
  key: string; label: string; color: string; opacity: number;
  ranges: Array<[string, string]>;
}
function condenseRanges(flags: boolean[]): Array<[number, number]> {
  const out: Array<[number, number]> = [];
  let start: number | null = null;
  for (let index = 0; index <= flags.length; index++) {
    const on = index < flags.length && flags[index];
    if (on && start === null) start = index;
    if (start !== null && !on) { out.push([start, index - 1]); start = null; }
  }
  return out;
}

export function computeHighlightBands(
  activeKeys: ReadonlySet<string>, market: BreadthMarket, dates: readonly string[],
  v20: readonly (number | null)[], v50: readonly (number | null)[], v200: readonly (number | null)[],
  thresholds?: { hot: number; cold: number },
): HighlightBand[] {
  if (!activeKeys.size || !dates.length) return [];
  const bands: HighlightBand[] = [];
  for (const meta of BREADTH_HIGHLIGHT_RULES) {
    if (!activeKeys.has(meta.key)) continue;
    const flags = dates.map((_, index) => evalBreadthRule(meta.key, market, v20[index], v50[index], v200[index], thresholds));
    const ranges = condenseRanges(flags).flatMap(([start, end]) =>
      dates[start] != null && dates[end] != null ? [[dates[start], dates[end]] as [string, string]] : []);
    if (ranges.length) bands.push({ key: meta.key, label: meta.full, color: meta.color, opacity: meta.opacity, ranges });
  }
  return bands;
}
