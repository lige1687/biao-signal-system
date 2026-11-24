import {
  alignDailySeriesToDates,
  alignErpZToDates,
  buildCausalPercentilePoints,
  buildCausalSmaPoints,
  rollingPercentileCausal,
  type DailyValuePoint,
  type ErpZBandRow,
  type HorizonForwardStats,
  type RuleIntent,
  type ScreenedEpisode,
} from "../market-style/breadthRegimeScreener";
import { rollingCleanMean } from "./projectionThresholds";

export type SupportedComboMetricId =
  | "cn-margin-buy"
  | "cn-margin-balance"
  | "vix"
  | "hy-oas"
  | "vxn"
  | "aaii"
  | "naaim"
  | "nfci"
  | "ofr-fsi"
  | "hs300-pe"
  | "sp500-cape";

export type BarFrequency = "daily" | "weekly" | "monthly";

export type MetricComboRuleSpec = {
  id: string;
  intent: RuleIntent;
  tier: "core" | "baseline";
  short: string;
  formula: string;
  basis: string;
  color: string;
  fill: string;
};

export type MetricCrossContextAtBar = {
  b20: number | null;
  b50: number | null;
  b200: number | null;
  erpValue: number | null;
  erpZ: number | null;
  marginRatio: number | null;
  marginPercentile: number | null;
  vix: number | null;
  vixTerm: number | null;
  hyOas: number | null;
};

export type MetricComboEvaluation = {
  supported: boolean;
  rules: MetricComboRuleSpec[];
  baselineLabel: string;
  horizonLabels: [string, string];
  byRule: Record<string, {
    rule: MetricComboRuleSpec;
    episodeCount: number;
    dayCount: number;
    isActiveLatest: boolean;
    ranges: Array<[string, string]>;
    episodes: ScreenedEpisode[];
  }>;
  markAreas: Array<[{ xAxis: string; itemStyle: { color: string } }, { xAxis: string }]>;
  episodes: ScreenedEpisode[];
  outcome: {
    rawEpisodeCount: number;
    dedupEpisodeCount: number;
    cooldownBars: number;
    h1: HorizonForwardStats;
    h2: HorizonForwardStats;
  };
  latestActiveRuleIds: string[];
  contextByDate: Map<string, MetricCrossContextAtBar>;
};

const finite = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);

const SUPPORTED_IDS = new Set<string>([
  "cn-margin-buy",
  "cn-margin-balance",
  "vix",
  "hy-oas",
  "vxn",
  "aaii",
  "naaim",
  "nfci",
  "ofr-fsi",
  "hs300-pe",
  "sp500-cape",
]);

export function isComboSupportedMetric(id: string): id is SupportedComboMetricId {
  return SUPPORTED_IDS.has(id);
}

/** Normalize YYYY-MM monthly dates to YYYY-MM-28 for causal as-of alignment against daily breadth/ERP. */
function normalizeDateForJoin(d: string): string {
  return d.length === 7 ? `${d}-28` : d;
}

export function buildMetricComboRuleSpecs(id: string): {
  baselineLabel: string;
  rules: MetricComboRuleSpec[];
} {
  switch (id) {
    case "cn-margin-buy":
      return {
        baselineLabel: "只看热度线",
        rules: [
          {
            id: "mb_dual_low_ice",
            intent: "bull",
            tier: "core",
            short: "借钱买股冷清+全场跌透",
            formula: "融资买入占成交额 ≤ 6.8%（没人借钱买），同时全A 50日与200日宽度都跌到 ≤ 20%",
            basis: "借钱炒股的人歇菜了，全场股票也跌透了（左侧见底观察区；该日频数据目前积累1年余，稳妥加仓可配「站上50日均线」）。",
            color: "#1d5f8a",
            fill: "rgba(29, 95, 138, 0.23)",
          },
          {
            id: "mb_crowded_fade",
            intent: "risk",
            tier: "core",
            short: "借钱追高过热+跌破20日线",
            formula: "近15天融资买入占比曾 ≥ 10.0%（大家抢着借钱买），今天50日宽度跌破一半且指数跌破20日均线",
            basis: "主升浪里光热度高不用怕，只有借钱追高后大半股票掉队、指数跌破20日线时才提醒减仓防跌（近1年余样本辅助观察）。",
            color: "#986737",
            fill: "rgba(152, 103, 55, 0.25)",
          },
          {
            id: "mb_raw_cold",
            intent: "bull",
            tier: "baseline",
            short: "只看冷清 ≤6.5%",
            formula: "融资买入占A股成交额比例 ≤ 6.5%",
            basis: "只看借钱买股冷不冷清；弱市缩量时可能继续冷，建议搭配均线走稳一起看。",
            color: "#327c72",
            fill: "rgba(50, 124, 114, 0.16)",
          },
          {
            id: "mb_raw_hot",
            intent: "neutral",
            tier: "baseline",
            short: "只看过热 ≥10.5%",
            formula: "融资买入占A股成交额比例 ≥ 10.5%",
            basis: "只看借钱买股热不热；牛市刚启动时也会很热，要看指数破没破位。",
            color: "#b45309",
            fill: "rgba(180, 83, 9, 0.16)",
          },
        ],
      };

    case "cn-margin-balance":
      return {
        baselineLabel: "只看余额高低",
        rules: [
          {
            id: "mbal_washout_ice",
            intent: "bull",
            tier: "core",
            short: "融资盘降到位+全场跌透",
            formula: "融资余额占流通市值降到近3年最低20%以内，同时50日与200日宽度都 ≤ 20%",
            basis: "借钱炒股的包袱已经卸得很轻，全场股票也跌透了（16年历史后60日平均涨+3.48%、比平时高2.50个百分点）。",
            color: "#0f766e",
            fill: "rgba(15, 118, 110, 0.23)",
          },
          {
            id: "mbal_overhang_fade",
            intent: "risk",
            tier: "core",
            short: "融资盘偏重+冲高破20日线",
            formula: "融资余额处于近3年偏高位置（≥P75），过半股票在年线下，近10天短线冲高（20日≥70%）后跌破50%且指数跌破20日均线",
            basis: "上方借钱套牢盘本来就重，弱势反弹冲一波又跌破20日线时容易往下砸（16年24次后20日平均跌1.48%，跑输平时1.73个百分点）。",
            color: "#a14a3b",
            fill: "rgba(161, 74, 59, 0.25)",
          },
          {
            id: "mbal_raw_p15",
            intent: "bull",
            tier: "baseline",
            short: "余额偏低 ≤3年P15",
            formula: "融资余额占流通市值处于过去3年最低15%区间",
            basis: "只看融资盘子在近3年里算偏轻。",
            color: "#327c72",
            fill: "rgba(50, 124, 114, 0.16)",
          },
          {
            id: "mbal_raw_p85",
            intent: "risk",
            tier: "baseline",
            short: "余额偏高 ≥3年P85",
            formula: "融资余额占流通市值处于过去3年最高15%区间",
            basis: "只看融资盘子在近3年里算偏重；慢牛里也会偏高，需搭配走势看。",
            color: "#986737",
            fill: "rgba(152, 103, 55, 0.16)",
          },
        ],
      };

    case "vix":
      return {
        baselineLabel: "只看VIX高低",
        rules: [
          {
            id: "vix_spike_credit_calm",
            intent: "bull",
            tier: "core",
            short: "股市恐慌·但债市没事",
            formula: "VIX ≥ 22 + 企业债利差 < 4.0%（公司借钱正常） + 过半股票在年线上 + 短线超跌",
            basis: "美股短线被吓跌，但债券市场很稳、企业没出真问题，多属情绪虚惊（后60日上涨率88.9%、平均涨+5.35%）。",
            color: "#0f766e",
            fill: "rgba(15, 118, 110, 0.25)",
          },
          {
            id: "vix_panic_unwind",
            intent: "bull",
            tier: "core",
            short: "恐慌冲高回落+止跌",
            formula: "近10天 VIX 曾冲上 ≥ 28，今天比最高点回落 ≥ 12% 且标普20日宽度止跌回升",
            basis: "极度恐慌劲儿开始消退、上涨股票同步变多（标普106段后60日上涨率77.1%）。",
            color: "#1f6feb",
            fill: "rgba(31, 111, 235, 0.23)",
          },
          {
            id: "vix_term_unwind",
            intent: "bull",
            tier: "core",
            short: "短线极度恐慌解除",
            formula: "近10天短期恐慌曾高于远期（VIX/VIX3M ≥ 1.02），今天回落到 < 0.98 恢复正常",
            basis: "大家不再抢买短期避险保险，最慌的时候已经过去（标普58段后120日上涨率75.4%）。",
            color: "#1d5f8a",
            fill: "rgba(29, 95, 138, 0.23)",
          },
          {
            id: "vix_credit_contagion",
            intent: "risk",
            tier: "core",
            short: "恐慌大跌+企业借钱变贵",
            formula: "VIX ≥ 25 同时企业债利差 ≥ 4.5%（或20天猛涨 ≥ 0.50个百分点）且50日宽度 < 40%",
            basis: "真风险警报：连公司发债借钱都明显变贵变难了（历史上20日平均最大回撤−9.1%）。",
            color: "#a14a3b",
            fill: "rgba(161, 74, 59, 0.26)",
          },
          {
            id: "vix_raw_20",
            intent: "neutral",
            tier: "baseline",
            short: "恐慌升温 ≥20",
            formula: "VIX ≥ 20",
            basis: "市场开始紧张的分界线；单凭它看不出见顶还是见底。",
            color: "#b45309",
            fill: "rgba(180, 83, 9, 0.14)",
          },
          {
            id: "vix_raw_30",
            intent: "risk",
            tier: "baseline",
            short: "极度恐慌 ≥30",
            formula: "VIX ≥ 30",
            basis: "市场极度恐慌区间；买点要等它见顶回落再动手。",
            color: "#986737",
            fill: "rgba(152, 103, 55, 0.20)",
          },
        ],
      };

    case "hy-oas":
      return {
        baselineLabel: "只看利差高低",
        rules: [
          {
            id: "hy_peak_ease",
            intent: "bull",
            tier: "core",
            short: "借钱利率见顶回落+企稳",
            formula: "近15天企业债利差曾升至 ≥ 3.6%，今天比高点回落 ≥ 0.18个百分点且股市20日宽度回升",
            basis: "企业借钱压力刚开始松口气，股市同步回暖（近3年样本后20/60日全部上涨，最大回撤仅−1.2%）。",
            color: "#0f766e",
            fill: "rgba(15, 118, 110, 0.25)",
          },
          {
            id: "hy_calm_vix_dip",
            intent: "bull",
            tier: "core",
            short: "债市很稳+美股被吓跌",
            formula: "企业债利差 < 4.0% 平稳，同时恐慌VIX ≥ 20 且标普20日宽度跌到 ≤ 32%",
            basis: "债券市场很淡定，说明美股急跌只是情绪吓跌、公司没出真事（后20/60日上涨率83.3%、后120日100%）。",
            color: "#1d5f8a",
            fill: "rgba(29, 95, 138, 0.23)",
          },
          {
            id: "hy_widen_contagion",
            intent: "risk",
            tier: "core",
            short: "借钱猛涨价+美股走弱",
            formula: "企业债利差 ≥ 4.2%（或20天猛涨 ≥ 0.35个百分点），同时VIX ≥ 22 且50日宽度 < 45%",
            basis: "企业借钱成本真涨上来了，叠加美股走弱，短期容易大晃动（历史后20日平均最大回撤超5%）。",
            color: "#a14a3b",
            fill: "rgba(161, 74, 59, 0.26)",
          },
          {
            id: "hy_raw_40",
            intent: "risk",
            tier: "baseline",
            short: "借钱偏贵 ≥4.0%",
            formula: "企业债利差 ≥ 4.0%",
            basis: "企业发债借钱开始偏贵的警戒线。",
            color: "#b45309",
            fill: "rgba(180, 83, 9, 0.16)",
          },
          {
            id: "hy_raw_50",
            intent: "risk",
            tier: "baseline",
            short: "借钱极贵 ≥5.0%",
            formula: "企业债利差 ≥ 5.0%",
            basis: "企业借钱明显困难的高压线。",
            color: "#986737",
            fill: "rgba(152, 103, 55, 0.22)",
          },
        ],
      };

    case "vxn":
      return {
        baselineLabel: "只看VXN高低",
        rules: [
          {
            id: "vxn_calm_dip",
            intent: "bull",
            tier: "core",
            short: "科技急跌·但债市没事",
            formula: "科技恐慌VXN ≥ 26 + 企业债利差 < 4.0% 平稳 + 过半股票在年线上 + 20日宽度 ≤ 32%",
            basis: "科技股短线跌得凶，但企业借钱很稳没出事，多半是正常洗盘回调。",
            color: "#0f766e",
            fill: "rgba(15, 118, 110, 0.24)",
          },
          {
            id: "vxn_panic_unwind",
            intent: "bull",
            tier: "core",
            short: "科技恐慌回落+止跌",
            formula: "近10天 VXN 曾 ≥ 32，今天比高点回落 ≥ 12% 且上涨股票变多",
            basis: "科技股恐慌情绪见顶消退，市场同步止跌。",
            color: "#1d5f8a",
            fill: "rgba(29, 95, 138, 0.23)",
          },
          {
            id: "vxn_contagion",
            intent: "risk",
            tier: "core",
            short: "科技大跌+企业借钱变贵",
            formula: "VXN ≥ 30 同时企业债利差 ≥ 4.2%（或20天猛涨 ≥ 0.35个百分点）且50日宽度 < 45%",
            basis: "不光科技股跌，连整体企业借钱都变贵了，需小心系统性回调。",
            color: "#a14a3b",
            fill: "rgba(161, 74, 59, 0.25)",
          },
          {
            id: "vxn_raw_25",
            intent: "neutral",
            tier: "baseline",
            short: "科技波动大 ≥25",
            formula: "VXN ≥ 25",
            basis: "纳指100波动加大分界。",
            color: "#b45309",
            fill: "rgba(180, 83, 9, 0.15)",
          },
          {
            id: "vxn_raw_35",
            intent: "risk",
            tier: "baseline",
            short: "科技极恐慌 ≥35",
            formula: "VXN ≥ 35",
            basis: "纳指100剧烈恐慌区间。",
            color: "#986737",
            fill: "rgba(152, 103, 55, 0.20)",
          },
        ],
      };

    case "aaii":
      return {
        baselineLabel: "只看散户情绪",
        rules: [
          {
            id: "aaii_bear_turn",
            intent: "bull",
            tier: "core",
            short: "散户极悲观+股市止跌",
            formula: "散户看涨减看跌 ≤ −15%（一片看空），同时标普20日宽度开始回升",
            basis: "散户吓破胆、而市场里上涨的股票其实已经在变多了，经典的反向买点。",
            color: "#0f766e",
            fill: "rgba(15, 118, 110, 0.24)",
          },
          {
            id: "aaii_bull_div",
            intent: "risk",
            tier: "core",
            short: "散户极乐观+多数股掉队",
            formula: "散户看涨减看跌 ≥ +20%（一片看多），但标普50日宽度 < 55% 且在往下掉",
            basis: "散户都在喊牛市，但底下很多股票已经涨不动了，小心追高挨套。",
            color: "#986737",
            fill: "rgba(152, 103, 55, 0.24)",
          },
          {
            id: "aaii_raw_low",
            intent: "bull",
            tier: "baseline",
            short: "只看悲观 ≤−15%",
            formula: "AAII 看涨减看跌 ≤ −15%",
            basis: "只看散户调查处于悲观区。",
            color: "#327c72",
            fill: "rgba(50, 124, 114, 0.16)",
          },
          {
            id: "aaii_raw_high",
            intent: "risk",
            tier: "baseline",
            short: "只看乐观 ≥+20%",
            formula: "AAII 看涨减看跌 ≥ +20%",
            basis: "只看散户调查处于乐观区。",
            color: "#b45309",
            fill: "rgba(180, 83, 9, 0.16)",
          },
        ],
      };

    case "naaim":
      return {
        baselineLabel: "只看机构仓位",
        rules: [
          {
            id: "naaim_washed_turn",
            intent: "bull",
            tier: "core",
            short: "机构轻仓+股市回升",
            formula: "机构平均仓位砍到 ≤ 45%，同时标普20日宽度开始回升",
            basis: "机构手里留了大量现金，一旦行情企稳回升，后续补仓买盘很足。",
            color: "#0f766e",
            fill: "rgba(15, 118, 110, 0.24)",
          },
          {
            id: "naaim_crowded_weak",
            intent: "risk",
            tier: "core",
            short: "机构满仓+多数股转弱",
            formula: "机构平均仓位高达 ≥ 90%，同时标普50日宽度 < 55% 且在往下掉",
            basis: "机构几乎把子弹打光了，同时越来越多股票掉队，后续接盘力变弱。",
            color: "#986737",
            fill: "rgba(152, 103, 55, 0.24)",
          },
          {
            id: "naaim_raw_low",
            intent: "bull",
            tier: "baseline",
            short: "只看轻仓 ≤40%",
            formula: "NAAIM 机构平均仓位 ≤ 40%",
            basis: "只看机构仓位处于低位。",
            color: "#327c72",
            fill: "rgba(50, 124, 114, 0.16)",
          },
          {
            id: "naaim_raw_high",
            intent: "risk",
            tier: "baseline",
            short: "只看满仓 ≥95%",
            formula: "NAAIM 机构平均仓位 ≥ 95%",
            basis: "只看机构仓位接近打满。",
            color: "#b45309",
            fill: "rgba(180, 83, 9, 0.16)",
          },
        ],
      };

    case "nfci":
    case "ofr-fsi":
      return {
        baselineLabel: "零轴松紧线",
        rules: [
          {
            id: "fci_loose_vix_dip",
            intent: "bull",
            tier: "core",
            short: "资金面宽松+股市吓跌",
            formula: "金融压力指数 < 0（大环境钱松），同时恐慌VIX ≥ 20 且20日宽度 ≤ 35%",
            basis: "宏观资金面很宽松，股市短线吓跌多半能很快缓过来。",
            color: "#0f766e",
            fill: "rgba(15, 118, 110, 0.24)",
          },
          {
            id: "fci_tight_weak",
            intent: "risk",
            tier: "core",
            short: "资金面收紧+多数股破位",
            formula: "金融压力指数 > 0（或近期快速收紧），同时标普50日宽度 < 45% 且继续回落",
            basis: "大环境钱变紧，叠加过半股票跌破均线，注意收紧仓位防大跌。",
            color: "#a14a3b",
            fill: "rgba(161, 74, 59, 0.25)",
          },
          {
            id: "fci_raw_above0",
            intent: "risk",
            tier: "baseline",
            short: "高于零轴 (>0 偏紧)",
            formula: "读数 > 0（相对长期历史平均水平偏紧）",
            basis: "零线为长期平均水平。",
            color: "#986737",
            fill: "rgba(152, 103, 55, 0.18)",
          },
        ],
      };

    case "hs300-pe":
    case "sp500-cape":
      return {
        baselineLabel: "只看贵贱分位",
        rules: [
          {
            id: "val_low_turn",
            intent: "bull",
            tier: "core",
            short: "估值便宜+上涨股变多",
            formula: "市盈率处于近10年最低25%以内，同时当月50日宽度比上月回升",
            basis: "长期够便宜，而且市场已经开始回暖，避免买在漫长阴跌半山腰。",
            color: "#0f766e",
            fill: "rgba(15, 118, 110, 0.24)",
          },
          {
            id: "val_high_weak",
            intent: "risk",
            tier: "core",
            short: "估值偏贵+多数股走弱",
            formula: "市盈率处于近10年最高20%区间，同时当月50日宽度跌破50%且比上月回落",
            basis: "牛市里光估值贵还会涨，只有当大半股票真跌破均线走弱时才需警惕。",
            color: "#986737",
            fill: "rgba(152, 103, 55, 0.24)",
          },
          {
            id: "val_raw_p20",
            intent: "bull",
            tier: "baseline",
            short: "只看便宜 ≤10年P20",
            formula: "市盈率处于过去10年最低20%区间",
            basis: "只看长期市盈率算便宜。",
            color: "#327c72",
            fill: "rgba(50, 124, 114, 0.16)",
          },
          {
            id: "val_raw_p80",
            intent: "risk",
            tier: "baseline",
            short: "只看偏贵 ≥10年P80",
            formula: "市盈率处于过去10年最高20%区间",
            basis: "只看长期市盈率算偏贵。",
            color: "#b45309",
            fill: "rgba(180, 83, 9, 0.16)",
          },
        ],
      };

    default:
      return { baselineLabel: "基础参考", rules: [] };
  }
}

function medianOf(nums: readonly number[]): number | null {
  if (!nums.length) return null;
  const sorted = [...nums].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 1 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

function computeForwardForBars(
  entryIndices: readonly number[],
  prices: readonly (number | null)[],
  horizonBars: number,
): HorizonForwardStats {
  const n = prices.length;
  const rets: number[] = [];
  const mdds: number[] = [];

  for (const s of entryIndices) {
    if (s < 0 || s + horizonBars >= n) continue;
    const entry = prices[s];
    const exit = prices[s + horizonBars];
    if (!finite(entry) || entry <= 0 || !finite(exit)) continue;
    rets.push(((exit / entry) - 1) * 100);
    let minP = entry;
    for (let k = s + 1; k <= s + horizonBars; k++) {
      if (finite(prices[k]) && prices[k]! < minP) minP = prices[k]!;
    }
    mdds.push(((minP / entry) - 1) * 100);
  }

  const baseRets: number[] = [];
  for (let i = 0; i + horizonBars < n; i++) {
    if (finite(prices[i]) && prices[i]! > 0 && finite(prices[i + horizonBars])) {
      baseRets.push(((prices[i + horizonBars]! / prices[i]!) - 1) * 100);
    }
  }
  const baselineMean = baseRets.length ? baseRets.reduce((a, b) => a + b, 0) / baseRets.length : null;
  const baselineWinRate = baseRets.length ? (baseRets.filter((v) => v > 0).length / baseRets.length) * 100 : null;

  if (!rets.length) {
    return {
      horizonBars,
      sampleCount: 0,
      winRate: null,
      meanReturn: null,
      medianReturn: null,
      avgMaxDrawdown: null,
      baselineWinRate,
      baselineMean,
      edgeMean: null,
    };
  }
  const meanReturn = rets.reduce((a, b) => a + b, 0) / rets.length;
  const winRate = (rets.filter((v) => v > 0).length / rets.length) * 100;
  return {
    horizonBars,
    sampleCount: rets.length,
    winRate,
    meanReturn,
    medianReturn: medianOf(rets),
    avgMaxDrawdown: mdds.reduce((a, b) => a + b, 0) / mdds.length,
    baselineWinRate,
    baselineMean,
    edgeMean: baselineMean != null ? meanReturn - baselineMean : null,
  };
}

export function evaluateMetricComboScreener({
  id,
  frequency = "daily",
  dates,
  prices,
  fullPricePoints,
  metricValues,
  fullMetricPoints,
  breadthPoints,
  erpBands,
  marginRatioPoints,
  vixPoints,
  vixTermPoints,
  hyOasPoints,
  activeIds,
}: {
  id: string;
  frequency?: BarFrequency;
  dates: readonly string[];
  prices: readonly (number | null)[];
  fullPricePoints?: readonly DailyValuePoint[];
  metricValues: readonly (number | null)[];
  fullMetricPoints?: readonly DailyValuePoint[];
  breadthPoints: readonly { date: string; breadth_20?: number | null; breadth_50?: number | null; breadth_200?: number | null }[];
  erpBands?: readonly ErpZBandRow[];
  marginRatioPoints?: readonly DailyValuePoint[];
  vixPoints?: readonly DailyValuePoint[];
  vixTermPoints?: readonly DailyValuePoint[];
  hyOasPoints?: readonly DailyValuePoint[];
  activeIds: ReadonlySet<string>;
}): MetricComboEvaluation {
  const { baselineLabel, rules } = buildMetricComboRuleSpecs(id);
  const horizonBarsPair: [number, number] =
    frequency === "monthly" ? [3, 12] : frequency === "weekly" ? [4, 12] : [20, 60];
  const horizonLabels: [string, string] =
    frequency === "monthly"
      ? ["后 3 个月", "后 12 个月"]
      : frequency === "weekly"
        ? ["后 4 周", "后 12 周"]
        : ["后 20 交易日", "后 60 交易日"];
  const cooldownBars = frequency === "daily" ? 5 : 2;

  if (!rules.length || !dates.length) {
    return {
      supported: rules.length > 0,
      rules,
      baselineLabel,
      horizonLabels,
      byRule: {},
      markAreas: [],
      episodes: [],
      outcome: {
        rawEpisodeCount: 0,
        dedupEpisodeCount: 0,
        cooldownBars,
        h1: computeForwardForBars([], prices, horizonBarsPair[0]),
        h2: computeForwardForBars([], prices, horizonBarsPair[1]),
      },
      latestActiveRuleIds: [],
      contextByDate: new Map(),
    };
  }

  const joinDates = dates.map(normalizeDateForJoin);
  const maxLag = frequency === "monthly" ? 35 : frequency === "weekly" ? 12 : 7;

  const b20Arr = alignDailySeriesToDates(
    joinDates,
    breadthPoints.map((p) => ({ date: p.date, value: finite(p.breadth_20) ? p.breadth_20 : null })),
    maxLag,
  );
  const b50Arr = alignDailySeriesToDates(
    joinDates,
    breadthPoints.map((p) => ({ date: p.date, value: finite(p.breadth_50) ? p.breadth_50 : null })),
    maxLag,
  );
  const b200Arr = alignDailySeriesToDates(
    joinDates,
    breadthPoints.map((p) => ({ date: p.date, value: finite(p.breadth_200) ? p.breadth_200 : null })),
    maxLag,
  );
  const alignedErp = alignErpZToDates(joinDates, erpBands ?? [], Math.max(10, maxLag));
  const marginVals = alignDailySeriesToDates(joinDates, marginRatioPoints, maxLag);
  const marginPctFull = buildCausalPercentilePoints(marginRatioPoints, 756, 120);
  const marginPct = alignDailySeriesToDates(joinDates, marginPctFull, maxLag);
  const vixVals = alignDailySeriesToDates(joinDates, vixPoints, maxLag);
  const vixTermVals = alignDailySeriesToDates(joinDates, vixTermPoints, maxLag);
  const hyVals = alignDailySeriesToDates(joinDates, hyOasPoints, Math.max(8, maxLag));
  const fullPriceMa20Pts = buildCausalSmaPoints(
    fullPricePoints ?? dates.map((d, idx) => ({ date: d, value: prices[idx] ?? null })),
    20,
  );
  const priceMa20Arr = alignDailySeriesToDates(joinDates, fullPriceMa20Pts, 3);

  // Precompute metric's own MA20 and 10Y monthly percentile if needed
  const cleanFull = (fullMetricPoints ?? dates.map((d, i) => ({ date: d, value: metricValues[i] }))).filter(
    (p): p is { date: string; value: number } => Boolean(p.date) && finite(p.value),
  );
  const ma20Map = rollingCleanMean(cleanFull, 20).byDate;
  const valPctArr =
    id === "hs300-pe" || id === "sp500-cape"
      ? (() => {
          const sorted = [...cleanFull].sort((a, b) => a.date.localeCompare(b.date));
          const pcts = rollingPercentileCausal(sorted.map((p) => p.value), 120, 36);
          const m = new Map<string, number>();
          sorted.forEach((p, idx) => {
            if (finite(pcts[idx])) m.set(p.date, pcts[idx]!);
          });
          return dates.map((d) => m.get(d) ?? null);
        })()
      : [];

  const contextByDate = new Map<string, MetricCrossContextAtBar>();
  dates.forEach((d, i) => {
    contextByDate.set(d, {
      b20: b20Arr[i] ?? null,
      b50: b50Arr[i] ?? null,
      b200: b200Arr[i] ?? null,
      erpValue: alignedErp[i]?.value ?? null,
      erpZ: alignedErp[i]?.z ?? null,
      marginRatio: marginVals[i] ?? null,
      marginPercentile: marginPct[i] ?? null,
      vix: vixVals[i] ?? null,
      vixTerm: vixTermVals[i] ?? null,
      hyOas: hyVals[i] ?? null,
    });
  });

  const evalAt = (ruleId: string, i: number): boolean => {
    const val = metricValues[i];
    const p = prices[i];
    const pMa20 = priceMa20Arr[i];
    const b20 = b20Arr[i];
    const b50 = b50Arr[i];
    const b200 = b200Arr[i];
    const mPct = marginPct[i];
    const vx = id === "vix" ? val : vixVals[i];
    const vt = vixTermVals[i];
    const hy = id === "hy-oas" ? val : hyVals[i];

    switch (ruleId) {
      // CN Margin Buy
      case "mb_raw_cold":
        return finite(val) && val <= 6.5;
      case "mb_raw_hot":
        return finite(val) && val >= 10.5;
      case "mb_dual_low_ice":
        return finite(val)
          && val <= 6.8
          && finite(b50)
          && b50 <= 20
          && (!finite(b200) || b200 <= 20);
      case "mb_light_ignite": {
        if (!finite(val) || !finite(b20) || b20 < 50) return false;
        if (finite(mPct) && mPct >= 65) return false;
        const ma = ma20Map.get(dates[i]);
        return finite(ma) && val > ma;
      }
      case "mb_crowded_fade": {
        if (!finite(p) || !finite(pMa20) || p >= pMa20 || !finite(b50) || b50 >= 50) return false;
        for (let j = Math.max(0, i - 15); j <= i; j++) {
          if (finite(metricValues[j]) && metricValues[j]! >= 10.0) return true;
        }
        return false;
      }

      // CN Margin Balance
      case "mbal_raw_p15":
        return finite(mPct) && mPct <= 15;
      case "mbal_raw_p85":
        return finite(mPct) && mPct >= 85;
      case "mbal_washout_ice":
        return finite(mPct)
          && mPct <= 20
          && finite(b50)
          && b50 <= 20
          && (!finite(b200) || b200 <= 20);
      case "mbal_overhang_fade": {
        if (
          i < 3
          || !finite(mPct)
          || mPct < 75
          || !finite(p)
          || !finite(pMa20)
          || p >= pMa20
          || !finite(b200)
          || b200 >= 50
          || !finite(b20)
          || b20 >= 50
        ) {
          return false;
        }
        for (let j = Math.max(0, i - 10); j < i; j++) {
          if (finite(b20Arr[j]) && b20Arr[j]! >= 70) return true;
        }
        return false;
      }

      // VIX
      case "vix_raw_20":
        return finite(vx) && vx >= 20;
      case "vix_raw_30":
        return finite(vx) && vx >= 30;
      case "vix_spike_credit_calm":
        return finite(vx)
          && vx >= 22
          && finite(hy)
          && hy < 4.0
          && finite(b200)
          && b200 > 50
          && (
            (finite(b20) && b20 <= 30)
            || (vx <= 30 && finite(vt) && vt >= 1.0)
          );
      case "vix_panic_unwind": {
        if (i < 3 || !finite(vx) || !finite(b20) || !finite(b20Arr[i - 3]) || b20 <= b20Arr[i - 3]!) return false;
        let peak = -Infinity;
        for (let j = Math.max(0, i - 10); j <= i; j++) {
          const pv = id === "vix" ? metricValues[j] : vixVals[j];
          if (finite(pv) && pv > peak) peak = pv;
        }
        return peak >= 28 && vx <= peak * 0.88;
      }
      case "vix_term_unwind": {
        if (i < 1 || !finite(vt) || vt >= 0.98) return false;
        for (let j = Math.max(0, i - 10); j < i; j++) {
          if (finite(vixTermVals[j]) && vixTermVals[j]! >= 1.02) return true;
        }
        return false;
      }
      case "vix_credit_contagion": {
        if (!finite(vx) || vx < 25 || !finite(hy) || !finite(b50) || b50 >= 40) return false;
        if (hy >= 4.5) return true;
        const prevHy = i >= 20 ? (id === "hy-oas" ? metricValues[i - 20] : hyVals[i - 20]) : null;
        return finite(prevHy) && hy - prevHy >= 0.50;
      }

      // HY OAS
      case "hy_raw_40":
        return finite(hy) && hy >= 4.0;
      case "hy_raw_50":
        return finite(hy) && hy >= 5.0;
      case "hy_peak_ease": {
        if (i < 3 || !finite(hy) || !finite(b20) || !finite(b20Arr[i - 3]) || b20 <= b20Arr[i - 3]!) return false;
        let peak = -Infinity;
        for (let j = Math.max(0, i - 15); j <= i; j++) {
          const ph = id === "hy-oas" ? metricValues[j] : hyVals[j];
          if (finite(ph) && ph > peak) peak = ph;
        }
        return peak >= 3.6 && hy <= peak - 0.18;
      }
      case "hy_calm_vix_dip":
        return finite(hy) && hy < 4.0 && finite(vx) && vx >= 20 && finite(b20) && b20 <= 32;
      case "hy_widen_contagion": {
        if (!finite(hy) || !finite(vx) || vx < 22 || !finite(b50) || b50 >= 45) return false;
        if (hy >= 4.2) return true;
        const prevHy = i >= 20 ? (id === "hy-oas" ? metricValues[i - 20] : hyVals[i - 20]) : null;
        return finite(prevHy) && hy - prevHy >= 0.35;
      }

      // VXN
      case "vxn_raw_25":
        return finite(val) && val >= 25;
      case "vxn_raw_35":
        return finite(val) && val >= 35;
      case "vxn_calm_dip":
        return finite(val) && val >= 26 && finite(hy) && hy < 4.0 && finite(b200) && b200 > 50 && finite(b20) && b20 <= 32;
      case "vxn_panic_unwind": {
        if (i < 3 || !finite(val) || !finite(b20) || !finite(b20Arr[i - 3]) || b20 <= b20Arr[i - 3]!) return false;
        let peak = -Infinity;
        for (let j = Math.max(0, i - 10); j <= i; j++) {
          if (finite(metricValues[j]) && metricValues[j]! > peak) peak = metricValues[j]!;
        }
        return peak >= 32 && val <= peak * 0.88;
      }
      case "vxn_contagion": {
        if (!finite(val) || val < 30 || !finite(hy) || !finite(b50) || b50 >= 45) return false;
        if (hy >= 4.2) return true;
        const prevHy = i >= 20 ? hyVals[i - 20] : null;
        return finite(prevHy) && hy - prevHy >= 0.35;
      }

      // AAII (weekly)
      case "aaii_raw_low":
        return finite(val) && val <= -15;
      case "aaii_raw_high":
        return finite(val) && val >= 20;
      case "aaii_bear_turn":
        return i >= 1 && finite(val) && val <= -15 && finite(b20) && finite(b20Arr[i - 1]) && b20 > b20Arr[i - 1]!;
      case "aaii_bull_div":
        return i >= 2 && finite(val) && val >= 20 && finite(b50) && finite(b50Arr[i - 2]) && b50 < 55 && b50 < b50Arr[i - 2]!;

      // NAAIM (weekly)
      case "naaim_raw_low":
        return finite(val) && val <= 40;
      case "naaim_raw_high":
        return finite(val) && val >= 95;
      case "naaim_washed_turn":
        return i >= 1 && finite(val) && val <= 45 && finite(b20) && finite(b20Arr[i - 1]) && b20 > b20Arr[i - 1]!;
      case "naaim_crowded_weak":
        return i >= 2 && finite(val) && val >= 90 && finite(b50) && finite(b50Arr[i - 2]) && b50 < 55 && b50 < b50Arr[i - 2]!;

      // NFCI / OFR-FSI
      case "fci_raw_above0":
        return finite(val) && val > 0;
      case "fci_loose_vix_dip":
        return finite(val) && val < 0 && finite(vx) && vx >= 20 && finite(b20) && b20 <= 35;
      case "fci_tight_weak": {
        const slopeStep = id === "nfci" ? 4 : 20;
        const slopeThresh = id === "nfci" ? 0.08 : 0.6;
        const marginalTight =
          i >= slopeStep
          && finite(val)
          && finite(metricValues[i - slopeStep])
          && val - metricValues[i - slopeStep]! >= slopeThresh;
        const lookbackB = id === "nfci" ? 1 : 5;
        return i >= lookbackB
          && finite(val)
          && (val > 0 || marginalTight)
          && finite(b50)
          && finite(b50Arr[i - lookbackB])
          && b50 < 45
          && b50 < b50Arr[i - lookbackB]!;
      }

      // Monthly PE / CAPE
      case "val_raw_p20":
        return finite(valPctArr[i]) && valPctArr[i]! <= 20;
      case "val_raw_p80":
        return finite(valPctArr[i]) && valPctArr[i]! >= 80;
      case "val_low_turn":
        return i >= 1 && finite(valPctArr[i]) && valPctArr[i]! <= 25 && finite(b50) && finite(b50Arr[i - 1]) && b50 > b50Arr[i - 1]!;
      case "val_high_weak":
        return i >= 1 && finite(valPctArr[i]) && valPctArr[i]! >= 80 && finite(b50) && finite(b50Arr[i - 1]) && b50 < 50 && b50 < b50Arr[i - 1]!;

      default:
        return false;
    }
  };

  const byRule: MetricComboEvaluation["byRule"] = {};
  const markAreas: MetricComboEvaluation["markAreas"] = [];
  const activeEpisodes: ScreenedEpisode[] = [];

  for (const rule of rules) {
    const flags = dates.map((_, i) => evalAt(rule.id, i));
    const ranges: Array<[string, string]> = [];
    const episodes: ScreenedEpisode[] = [];
    let start: number | null = null;
    let dayCount = 0;

    for (let i = 0; i <= flags.length; i++) {
      const on = i < flags.length && flags[i];
      if (on) {
        dayCount++;
        if (start === null) start = i;
      } else if (start !== null) {
        const end = i - 1;
        const sDate = dates[start];
        const eDate = dates[end];
        if (sDate != null && eDate != null) {
          ranges.push([sDate, eDate]);
          episodes.push({
            id: `${rule.id}:${sDate}:${eDate}`,
            ruleId: rule.id,
            ruleLabel: rule.short,
            color: rule.color,
            startDate: sDate,
            endDate: eDate,
            startIndex: start,
            endIndex: end,
            days: end - start + 1,
            startPrice: finite(prices[start]) ? prices[start]! : null,
          });
        }
        start = null;
      }
    }

    const isActiveLatest = flags.length > 0 && flags[flags.length - 1];
    byRule[rule.id] = { rule, episodeCount: episodes.length, dayCount, isActiveLatest, ranges, episodes };

    if (activeIds.has(rule.id)) {
      activeEpisodes.push(...episodes);
      for (const ep of episodes) {
        let vStart = ep.startDate;
        let vEnd = ep.endDate;
        if (ep.endIndex + 1 < dates.length) {
          vEnd = dates[ep.endIndex + 1];
        } else if (vStart === vEnd && ep.startIndex > 0) {
          vStart = dates[ep.startIndex - 1];
        }
        if (vStart !== vEnd) {
          markAreas.push([{ xAxis: vStart, itemStyle: { color: rule.fill } }, { xAxis: vEnd }]);
        }
      }
    }
  }

  activeEpisodes.sort((a, b) => a.startDate.localeCompare(b.startDate));

  // Cooldown-deduplicated forward return outcome
  const sortedEps = [...activeEpisodes].sort((a, b) => a.startIndex - b.startIndex || a.endIndex - b.endIndex);
  const merged: Array<{ startIndex: number; endIndex: number }> = [];
  for (const ep of sortedEps) {
    const last = merged[merged.length - 1];
    if (last && ep.startIndex - last.endIndex <= cooldownBars) {
      last.endIndex = Math.max(last.endIndex, ep.endIndex);
    } else {
      merged.push({ startIndex: ep.startIndex, endIndex: ep.endIndex });
    }
  }
  const entryIndices = merged.map((m) => m.startIndex);

  const latestActiveRuleIds = rules
    .filter((r) => byRule[r.id]?.isActiveLatest)
    .sort((a, b) => (a.tier === "core" ? 0 : 1) - (b.tier === "core" ? 0 : 1))
    .map((r) => r.id);

  return {
    supported: true,
    rules,
    baselineLabel,
    horizonLabels,
    byRule,
    markAreas,
    episodes: activeEpisodes,
    outcome: {
      rawEpisodeCount: activeEpisodes.length,
      dedupEpisodeCount: merged.length,
      cooldownBars,
      h1: computeForwardForBars(entryIndices, prices, horizonBarsPair[0]),
      h2: computeForwardForBars(entryIndices, prices, horizonBarsPair[1]),
    },
    latestActiveRuleIds,
    contextByDate,
  };
}
