import type { HighlightBand } from "../trend/zones";
import type { BreadthHorizon, BreadthReadingPoint } from "./breadthReadingTypes";

export type BreadthScreenerMarket = "cn" | "us";
export type ScreenerGroupKey = "single" | "combo" | "cross" | "risk";
export type ErpBreadthCrossFilter = "all" | "cheap_low" | "cheap_turn" | "macro_bull" | "rich_weak";
export type RuleIntent = "bull" | "risk" | "neutral";
export type RuleDisplayTier = "core" | "baseline" | "hidden";

/** Curated highest-efficacy, full-history combinations per market (3 buy + 2 sell). */
export const CORE_RULE_IDS_BY_MARKET: Record<BreadthScreenerMarket, readonly string[]> = {
  cn: [
    "dual_low_w3",
    "erp_cheap_w3",
    "erp_cheap_turn",
    "hot_retreat_break",
    "weak_base_rally_fade",
  ],
  us: [
    "reversal_bottom",
    "bull_pullback_turn",
    "us_vix_panic_unwind",
    "weak_base_rally_fade",
    "bull_base_break",
  ],
};

/** Raw breadth level rulers & supplemental short-history rules kept behind a 1-click collapsible toggle. */
export const BASELINE_RULE_IDS_BY_MARKET: Record<BreadthScreenerMarket, readonly string[]> = {
  cn: [
    "hist_low",
    "hist_high",
    "stage_bottom",
    "reversal_top",
    "reversal_bottom",
  ],
  us: [
    "hist_low",
    "hist_high",
    "stage_bottom",
    "reversal_top",
    "us_vix_term_unwind",
    "us_vix_spike_credit_calm",
    "us_credit_contagion",
  ],
};

/** Four core raw breadth level rulers shared by both markets. */
export const BASELINE_RULE_IDS: readonly string[] = [
  "hist_low",
  "hist_high",
  "stage_bottom",
  "reversal_top",
];

export type ErpZBandRow = {
  date: string;
  value: number | null;
  z: number | null;
};

export type DailyValuePoint = {
  date: string;
  value: number | null;
};

export type AlignedErpPoint = {
  date: string;
  value: number | null;
  z: number | null;
};

export type AlignedMacroPoint = {
  marginRatio: number | null;
  marginPercentile: number | null;
  vix: number | null;
  vixTerm: number | null;
  hyOas: number | null;
  priceMa20: number | null;
  priceMa50: number | null;
  priceMa60: number | null;
};

export type BreadthScreenerAuxInputs = {
  marginRatio?: readonly DailyValuePoint[];
  vix?: readonly DailyValuePoint[];
  vixTerm?: readonly DailyValuePoint[];
  hyOas?: readonly DailyValuePoint[];
  fullPrice?: readonly DailyValuePoint[];
};

export type BreadthScreenerRuleMeta = {
  id: string;
  group: ScreenerGroupKey;
  intent: RuleIntent;
  tier?: RuleDisplayTier;
  short: string;
  formula: string;
  basis: string;
  coverageNote?: string;
  color: string;
  opacity: number;
  skipStartMarker?: boolean;
  needsErp?: boolean;
};

export type ScreenedEpisode = {
  id: string;
  ruleId: string;
  ruleLabel: string;
  intent?: RuleIntent;
  color: string;
  startDate: string;
  endDate: string;
  startIndex: number;
  endIndex: number;
  days: number;
  startPrice: number | null;
};

export type HorizonForwardStats = {
  horizonBars: number;
  sampleCount: number;
  winRate: number | null;
  meanReturn: number | null;
  medianReturn: number | null;
  avgMaxDrawdown: number | null;
  baselineWinRate: number | null;
  baselineMean: number | null;
  edgeMean: number | null;
};

export type EpisodeOutcomeSummary = {
  rawEpisodeCount: number;
  dedupEpisodeCount: number;
  cooldownBars: number;
  d20: HorizonForwardStats;
  d60: HorizonForwardStats;
};

export type OutcomeByIntentSummary = {
  bull: EpisodeOutcomeSummary;
  risk: EpisodeOutcomeSummary;
  neutral: EpisodeOutcomeSummary;
};

export type RuleMatchSummary = {
  rule: BreadthScreenerRuleMeta;
  episodeCount: number;
  dayCount: number;
  isActiveLatest: boolean;
  ranges: Array<[string, string]>;
  episodes: ScreenedEpisode[];
};

export type ScreenerEvaluation = {
  byRule: Record<string, RuleMatchSummary>;
  bands: HighlightBand[];
  markers: Array<{
    name: string;
    value: [string, number];
    ruleId: string;
    episodeId: string;
    itemStyle: { color: string };
    label: { color: string; backgroundColor: string };
  }>;
  episodes: ScreenedEpisode[];
  alignedErp: (AlignedErpPoint | null)[];
  alignedMacro: AlignedMacroPoint[];
  outcome: EpisodeOutcomeSummary;
  outcomeByIntent: OutcomeByIntentSummary;
  activeIntents: RuleIntent[];
  latestActiveRuleIds: string[];
};

export const SCREENER_GROUP_LABELS: Record<ScreenerGroupKey, string> = {
  single: "单周期水位基座",
  combo: "量化宽度推力与买点",
  cross: "机构跨维黄金共振",
  risk: "机构风控与背离预警",
};

const finite = (value: unknown): value is number =>
  typeof value === "number" && Number.isFinite(value);

function dayGap(earlier: string, later: string): number {
  return Math.round(
    (Date.parse(`${later}T00:00:00Z`) - Date.parse(`${earlier}T00:00:00Z`)) / 86_400_000,
  );
}

/** Causal two-pointer alignment from ERP dates to price/breadth dates with max-lag guard. */
export function alignErpZToDates(
  dates: readonly string[],
  erpBands: readonly ErpZBandRow[],
  maxLagDays = 10,
): (AlignedErpPoint | null)[] {
  if (!dates.length || !erpBands.length) return dates.map(() => null);
  const sortedErp = erpBands.every((row, idx) => idx === 0 || row.date >= erpBands[idx - 1].date)
    ? erpBands
    : [...erpBands].sort((a, b) => a.date.localeCompare(b.date));

  let pointer = -1;
  return dates.map((day) => {
    while (pointer + 1 < sortedErp.length && sortedErp[pointer + 1].date <= day) {
      pointer++;
    }
    if (pointer < 0) return null;
    const candidate = sortedErp[pointer];
    if (dayGap(candidate.date, day) > maxLagDays) return null;
    return {
      date: candidate.date,
      value: finite(candidate.value) ? candidate.value : null,
      z: finite(candidate.z) ? candidate.z : null,
    };
  });
}

function yearsBeforeIso(day: string, years: number): string {
  const yr = Number(day.slice(0, 4)) - years;
  const cand = `${yr}${day.slice(4)}`;
  const parsed = Date.parse(`${cand}T00:00:00Z`);
  return Number.isFinite(parsed) && new Date(parsed).toISOString().slice(0, 10) === cand
    ? cand
    : `${yr}-02-28`;
}

/** Causal rolling Z-score over [date - lookbackYears, date), strictly excluding current and future observations. */
export function buildCausalRollingErpZ(
  erpBands: readonly ErpZBandRow[],
  lookbackYears = 1,
  minObs = 180,
): ErpZBandRow[] {
  if (!erpBands.length) return [];
  const sorted = erpBands.every((row, idx) => idx === 0 || row.date >= erpBands[idx - 1].date)
    ? erpBands
    : [...erpBands].sort((a, b) => a.date.localeCompare(b.date));
  let start = 0;
  return sorted.map((row, idx) => {
    const cutoff = yearsBeforeIso(row.date, lookbackYears);
    while (start < idx && sorted[start].date < cutoff) start++;
    if (sorted[0].date > cutoff || !finite(row.value)) {
      return { date: row.date, value: finite(row.value) ? row.value : null, z: null };
    }
    let sum = 0;
    let n = 0;
    for (let k = start; k < idx; k++) {
      const v = sorted[k].value;
      if (finite(v)) {
        sum += v;
        n++;
      }
    }
    if (n < minObs) {
      return { date: row.date, value: row.value, z: null };
    }
    const mean = sum / n;
    let sq = 0;
    for (let k = start; k < idx; k++) {
      const v = sorted[k].value;
      if (finite(v)) sq += (v - mean) ** 2;
    }
    const sd = Math.sqrt(sq / n);
    return { date: row.date, value: row.value, z: sd > 0 ? (row.value - mean) / sd : null };
  });
}

/** Causal as-of alignment for daily macro/micro series (VIX, VIX/VIX3M, HY OAS, Margin Ratio). */
export function alignDailySeriesToDates(
  dates: readonly string[],
  points: readonly DailyValuePoint[] | undefined,
  maxLagDays = 6,
): (number | null)[] {
  if (!dates.length || !points?.length) return dates.map(() => null);
  const valid = points.filter((p) => p.date && finite(p.value));
  if (!valid.length) return dates.map(() => null);
  const sorted = valid.every((row, idx) => idx === 0 || row.date >= valid[idx - 1].date)
    ? valid
    : [...valid].sort((a, b) => a.date.localeCompare(b.date));

  let pointer = -1;
  return dates.map((day) => {
    while (pointer + 1 < sorted.length && sorted[pointer + 1].date <= day) {
      pointer++;
    }
    if (pointer < 0) return null;
    const candidate = sorted[pointer];
    return dayGap(candidate.date, day) <= maxLagDays ? candidate.value : null;
  });
}

/** Precompute causal simple moving average on full daily price points before window slicing. */
export function buildCausalSmaPoints(
  points: readonly DailyValuePoint[] | undefined,
  windowBars: number,
): DailyValuePoint[] {
  if (!points?.length || windowBars <= 0) return [];
  const valid = points.filter((p) => p.date && finite(p.value));
  const sorted = valid.every((row, idx) => idx === 0 || row.date >= valid[idx - 1].date)
    ? valid
    : [...valid].sort((a, b) => a.date.localeCompare(b.date));
  const out: DailyValuePoint[] = [];
  let sum = 0;
  for (let i = 0; i < sorted.length; i++) {
    sum += sorted[i].value!;
    if (i >= windowBars) sum -= sorted[i - windowBars].value!;
    out.push({
      date: sorted[i].date,
      value: i + 1 >= windowBars ? sum / windowBars : null,
    });
  }
  return out;
}

function rollingSmaArray(values: readonly (number | null)[], windowBars: number): (number | null)[] {
  return values.map((_, idx) => {
    if (idx + 1 < windowBars) return null;
    let sum = 0;
    for (let j = idx - windowBars + 1; j <= idx; j++) {
      if (!finite(values[j])) return null;
      sum += values[j]!;
    }
    return sum / windowBars;
  });
}
export function buildCausalPercentilePoints(
  points: readonly DailyValuePoint[] | undefined,
  windowBars = 756,
  minBars = 120,
): DailyValuePoint[] {
  if (!points?.length) return [];
  const valid = points.filter((p) => p.date && finite(p.value));
  const sorted = valid.every((row, idx) => idx === 0 || row.date >= valid[idx - 1].date)
    ? valid
    : [...valid].sort((a, b) => a.date.localeCompare(b.date));
  const pcts = rollingPercentileCausal(
    sorted.map((p) => p.value),
    windowBars,
    minBars,
  );
  return sorted.map((p, idx) => ({ date: p.date, value: pcts[idx] ?? null }));
}
export function rollingPercentileCausal(
  values: readonly (number | null)[],
  windowBars = 756,
  minBars = 120,
): (number | null)[] {
  const history: number[] = [];
  return values.map((v) => {
    if (!finite(v)) return null;
    let pct: number | null = null;
    if (history.length >= minBars) {
      const sliceStart = Math.max(0, history.length - windowBars);
      const len = history.length - sliceStart;
      let le = 0;
      for (let i = sliceStart; i < history.length; i++) {
        if (history[i] <= v) le++;
      }
      pct = (le / len) * 100;
    }
    history.push(v);
    return pct;
  });
}

export function buildScreenerRuleSpecs(
  market: BreadthScreenerMarket,
  horizon: BreadthHorizon,
): BreadthScreenerRuleMeta[] {
  const cold = market === "cn" ? 20 : 15;
  const hot = market === "cn" ? 80 : 85;
  const pullbackCold = market === "cn" ? 22 : 18;
  const zweigHigh = market === "cn" ? 75 : 80;
  const deemerBase = market === "cn" ? 30 : 28;

  const singleRules: BreadthScreenerRuleMeta[] = [
    {
      id: "hist_low",
      group: "single",
      intent: "bull",
      short: `${horizon}日低位 (近5年最冷10%)`,
      formula: `站上${horizon}日均线的股票比例处于近5年最低10%区间`,
      basis: "只看这一项指标自身在近5年里算不算跌透。",
      color: "#0f766e",
      opacity: 0.16,
    },
    {
      id: "hist_high",
      group: "single",
      intent: "neutral",
      short: `${horizon}日高位 (近5年最热10%)`,
      formula: `站上${horizon}日均线的股票比例处于近5年最高10%区间`,
      basis: "只看这一项指标在近5年里算不算最热；大牛市里可以在高位待很久。",
      color: "#b45309",
      opacity: 0.16,
    },
    {
      id: "stage_bottom",
      group: "single",
      intent: "bull",
      short: `超卖低位 50日≤${cold}%`,
      formula: `站上50日均线的股票比例 ≤ ${cold}%`,
      basis: `全场不到 ${cold}% 的股票在50日均线上，说明短期普遍超跌。`,
      color: "#2b6cb0",
      opacity: 0.14,
    },
    {
      id: "stage_top",
      group: "single",
      intent: "neutral",
      short: `普涨高位 50日≥${hot}%`,
      formula: `站上50日均线的股票比例 ≥ ${hot}%`,
      basis: `超过 ${hot}% 的股票都在50日均线上，属于全面普涨。`,
      color: "#9b744d",
      opacity: 0.14,
    },
    {
      id: "bull_base",
      group: "single",
      intent: "bull",
      short: "大势向上 200日>50%",
      formula: "超过一半的股票站在200日年线上方",
      basis: "过半股票在年线上，说明整体大环境偏强。",
      color: "#47758c",
      opacity: 0.07,
      skipStartMarker: true,
    },
    {
      id: "bear_base",
      group: "single",
      intent: "risk",
      short: "大势偏弱 200日<50%",
      formula: "超过一半的股票跌在200日年线下方",
      basis: "过半股票在年线下，说明整体处于弱势或只涨少数权重股。",
      color: "#8c735b",
      opacity: 0.07,
      skipStartMarker: true,
    },
  ];

  const comboRules: BreadthScreenerRuleMeta[] = [
    {
      id: "bull_pullback_turn",
      group: "combo",
      intent: "bull",
      short: "牛市急跌后止跌",
      formula: `过半股票仍在年线上（200日>50%），近5天20日宽度曾急跌到 ≤${pullbackCold}%，今天重新掉头回升`,
      basis: "牛市里的洗盘回头买点：大趋势没坏，等短线急跌止住再买（美股46年81次后20日上涨率80.2%）。",
      color: "#0f766e",
      opacity: 0.22,
    },
    {
      id: "zweig_thrust",
      group: "combo",
      intent: "bull",
      short: "两周买盘爆发 (Zweig)",
      formula: `12个交易日内站上20日线的股票从 ≤20% 迅速猛增到 ≥${zweigHigh}%`,
      basis: "两周内买盘横扫全场，代表大资金集中进场（上证33年96次后20日平均涨+2.51%）。",
      color: "#1f6feb",
      opacity: 0.24,
    },
    {
      id: "deemer_thrust",
      group: "combo",
      intent: "bull",
      short: "中期买盘猛增 (Deemer)",
      formula: `10天前50日宽度 ≤${deemerBase}%，10个交易日内大涨超过25个百分点`,
      basis: "大批股票在两周内集中站回50日均线，确认波段回暖。",
      color: "#1d5f8a",
      opacity: 0.22,
    },
    {
      id: "washout_thrust",
      group: "combo",
      intent: "bull",
      short: "超跌回升观察",
      formula: `前10天曾跌至低位，当日20日宽度较5天前回升≥10个百分点`,
      basis: "历史对照项。",
      color: "#2b6cb0",
      opacity: 0.22,
    },
    {
      id: "bull_pullback",
      group: "combo",
      intent: "bull",
      short: `牛市急跌洗盘 200日>50%+20日≤${cold}%`,
      formula: `过半股票仍在200日年线上，同时20日短期宽度急跌到 ≤${cold}%`,
      basis: "上升趋势里的短线超跌区。",
      color: "#246b61",
      opacity: 0.18,
    },
    {
      id: "reversal_bottom",
      group: "combo",
      intent: "bull",
      short: `长短线都跌透 50/200日≤${cold}%`,
      formula: `站上50日均线和200日年线的股票比例同一天都掉到 ${cold}% 以下`,
      basis: market === "us"
        ? "美股恐慌大底：标普2006年以来8次后20/60日上涨率均达87.5%（平均涨+5.84% / +10.73%），近5年2次100%上涨。"
        : "仅作全场极寒区水位观察：A股熊市阴跌期常在半山腰触发（上证33年62次后60日上涨率仅37.7%、均跌−2.93%）；稳妥买点看核心区「跌透后站回50日均线」。",
      color: "#0f766e",
      opacity: 0.23,
    },
    {
      id: "dual_low_w3",
      group: "combo",
      intent: "bull",
      short: "跌透后站回50日均线",
      formula: `近30天内出现过长短线都跌透（50日与200日宽度均≤${cold}%），今天指数收盘重新站上自身50日均线`,
      basis: "不抢最低点，等大盘自己走稳站回50日线再进（避开假反弹）：1993年以来三个年代后60日全部赚钱，近5年上涨率80.0%(+5.24%)。",
      color: "#1d5f8a",
      opacity: 0.24,
    },
    {
      id: "dual_low_turn",
      group: "combo",
      intent: "bull",
      short: "双低右侧拐头",
      formula: `历史对照项`,
      basis: "历史对照项。",
      color: "#2b6cb0",
      opacity: 0.22,
    },
  ];

  const crossCommon: BreadthScreenerRuleMeta[] = [
    {
      id: "erp_cheap_w3",
      group: "cross",
      intent: "bull",
      short: "股票便宜+跌透后站上50日线",
      formula: `股债利差 ≥ +1σ（买股比买国债划算），近30天内50日宽度曾跌到 ≤${cold}%，今天指数站上50日均线`,
      basis: "既便宜、又跌透、大盘还重新走稳：上证33年历史后60日上涨率76.0%(平均+7.11%)，早中近三个年代上涨率都在69%~83%。",
      color: "#246b61",
      opacity: 0.24,
      needsErp: true,
    },
    {
      id: "erp_cheap_turn",
      group: "cross",
      intent: "bull",
      short: "估值便宜+宽度回暖",
      formula: `股债利差 ≥ +1σ（偏便宜），近15天内50日宽度曾跌到 ≤${cold}%，今天20/50日宽度均较5天前回升且20日 ≥ 50日`,
      basis: "估值划算叠加宽基参与面先行拐头：上证近5年13次后60日上涨率84.6%（均涨+7.14%、较基准+6.58pp），全史43次后20/60日均65.1%上涨。",
      color: "#246b61",
      opacity: 0.22,
      needsErp: true,
    },
    {
      id: "erp_cheap_low",
      group: "cross",
      intent: "bull",
      short: "股票便宜+多数股跌透",
      formula: `股债利差 ≥ +1.5σ（买股比买国债明显划算），同时50日宽度 ≤ ${cold}%`,
      basis: "适合长线攒筹码的低位区。",
      color: "#246b61",
      opacity: 0.20,
      needsErp: true,
    },
  ];

  const crossSpecific: BreadthScreenerRuleMeta[] = market === "cn"
    ? [
        {
          id: "cn_triple_bottom",
          group: "cross",
          intent: "bull",
          short: "股票便宜+融资盘轻",
          formula: "历史对照项",
          basis: "历史对照项。",
          color: "#1d5f8a",
          opacity: 0.24,
          needsErp: true,
        },
        {
          id: "cn_margin_washout",
          group: "cross",
          intent: "bull",
          short: "融资盘降到位+多数股跌透",
          formula: `融资余额占流通市值降到近3年最低20%以内，同时50日宽度 ≤ ${cold}%`,
          basis: "借钱炒股包袱卸轻叠加全场超跌。",
          color: "#2b6cb0",
          opacity: 0.22,
        },
      ]
    : [
        {
          id: "us_vix_spike_credit_calm",
          group: "cross",
          intent: "bull",
          short: "股市恐慌·但债市没事",
          formula: "恐慌VIX ≥ 22 + 企业债利差 HY OAS < 4.0% + 过半股票在年线上 + 短线超跌",
          basis: "美股短线被消息吓跌但信用债平稳（2023-11以来9次后60日上涨率88.9%、均涨+5.35%）；注意 FRED 公开 HY OAS 仅保留近3年，2023-11前无记录。",
          coverageNote: "HY OAS 仅覆盖 2023-11 至今",
          color: "#1d5f8a",
          opacity: 0.25,
        },
        {
          id: "us_vix_panic_unwind",
          group: "cross",
          intent: "bull",
          short: "恐慌冲高回落+止跌",
          formula: "近10天恐慌VIX曾冲上 ≥28，今天较峰值回落 ≥12% 且20日宽度较3天前回升",
          basis: "覆盖完整20年历史：极度恐慌消退且上涨股票同步增多（标普2006年以来58次后60日上涨率79.3%、均涨+5.42%/较基准+3.07pp；纳指+7.11%）。",
          color: "#1f6feb",
          opacity: 0.23,
        },
        {
          id: "us_vix_term_unwind",
          group: "cross",
          intent: "bull",
          short: "短线极度恐慌解除",
          formula: "近10天短期恐慌曾高于远期（VIX/VIX3M ≥ 1.02），今天回落至 0.98 以下恢复正常",
          basis: "覆盖2006年至今：期权避险抢购退潮（标普近5年9次后20日上涨率88.9%、均涨+3.11%，20年56次后20/60日均正向超额）。",
          color: "#1d5f8a",
          opacity: 0.23,
        },
      ];

  const riskCommon: BreadthScreenerRuleMeta[] = [
    {
      id: "climax_ma20_break",
      group: "risk",
      intent: "risk",
      short: "普涨过热后跌破20日线",
      formula: `近30天内超${hot}%的股票曾全面普涨（50日≥${hot}%），今天掉回一半以下（<50%）且指数跌破20日均线`,
      basis: "大涨热闹时不提前瞎猜顶，等过半股票掉队、指数跌破20日线再落袋止盈（上证33年84次后20日仅40.5%上涨）。",
      color: "#b45309",
      opacity: 0.24,
    },
    {
      id: "weak_base_rally_fade",
      group: "risk",
      intent: "risk",
      short: "大势偏弱+冲高破20日线",
      formula: "过半股票还在年线下（200日<50%），近10天短线猛冲过热（20日≥70%），今天掉回50%以下且指数跌破20日均线",
      basis: market === "us"
        ? "过半股票在年线下时的急拉反弹极易回吐：标普近5年6次后20/60日均跌−2.11%/−1.25%（跑输−2.98pp/−4.04pp），标普/纳指20年持续跑输基准。"
        : "弱势环境里的急拉反弹很容易打回原形：上证1993年以来93次后20日平均跌−1.52%（跑输基准−2.25pp），三个年代全部下跌。",
      color: "#a14a3b",
      opacity: 0.24,
    },
    {
      id: "hot_retreat_break",
      group: "risk",
      intent: "risk",
      short: "高热退潮·破20日线",
      formula: "近20天内50日宽度曾 ≥65% 或20日宽度曾 ≥80%（普涨过热），今天50日跌破45%、20日跌破35%且指数跌破20日均线",
      basis: "比80%普涨阈值更贴合A股结构行情：上证33年125次后20日仅39.2%上涨（均跌−1.33%、跑输−2.05pp），近5年与沪深300全史20/60日均稳定跑输。",
      color: "#b45309",
      opacity: 0.24,
    },
    {
      id: "bull_base_break",
      group: "risk",
      intent: "risk",
      short: "年线强弱失守",
      formula: "近20天内过半股票还在年线上（200日≥50%），今天200日跌破48%且50日<40%、20日<35%（中期格局转弱）",
      basis: "牛熊中轴由强转弱的破位预警（覆盖完整20年）：标普2006年以来34次后20日仅41.2%上涨（均跌−0.59%、跑输−1.37pp），纳指同期跑输−1.77pp。",
      color: "#986737",
      opacity: 0.24,
    },
    {
      id: "erp_rich_weak",
      group: "risk",
      intent: "risk",
      short: "股票偏贵+多数股走弱",
      formula: "股债利差 ≤ −1.5σ（偏贵）同时站上50日线股票不足一半",
      basis: "历史对照项。",
      color: "#986737",
      opacity: 0.23,
      needsErp: true,
    },
    {
      id: "bear_rally_trap",
      group: "risk",
      intent: "risk",
      short: "弱势反弹回落",
      formula: "历史对照项",
      basis: "历史对照项。",
      color: "#a14a3b",
      opacity: 0.23,
    },
    {
      id: "top_divergence",
      group: "risk",
      intent: "risk",
      short: "指数在高位·多数股掉队",
      formula: "指数离近60天最高点不到2%，但站上50日线的股票已不足一半（<50%）且比20天前少了8个百分点以上",
      basis: "只剩几只大权重股撑着指数、多数股票掉队；美股巨头行情中未破位时常继续慢涨，需等破位确认。",
      color: "#b45309",
      opacity: 0.22,
    },
    {
      id: "reversal_top",
      group: "risk",
      intent: "neutral",
      short: `长短线全热 50/200日≥${hot}%`,
      formula: `50日与200日均线上方股票比例同一天都 ≥ ${hot}%`,
      basis: "全场极热区。",
      color: "#9c5726",
      opacity: 0.20,
    },
  ];

  const riskSpecific: BreadthScreenerRuleMeta[] = market === "cn"
    ? [
        {
          id: "cn_margin_crowded_div",
          group: "risk",
          intent: "risk",
          short: "融资盘偏重+多数股走弱",
          formula: "历史对照项",
          basis: "历史对照项。",
          color: "#8c5a32",
          opacity: 0.22,
        },
      ]
    : [
        {
          id: "us_credit_contagion",
          group: "risk",
          intent: "risk",
          short: "恐慌大跌+企业借钱变贵",
          formula: "恐慌VIX ≥ 25 + 企业债利差 HY OAS ≥ 4.5%（或20天猛涨 ≥0.5pp） + 站上50日线股票不足4成",
          basis: "信用债压力警报（2025-03～04急跌期20日平均最大回撤−9.1%）；注意 FRED 公开 HY OAS 仅保留近3年，2023-11前无记录。",
          coverageNote: "HY OAS 仅覆盖 2023-11 至今",
          color: "#a14a3b",
          opacity: 0.25,
        },
      ];

  const coreSet = new Set(CORE_RULE_IDS_BY_MARKET[market]);
  const baselineSet = new Set(BASELINE_RULE_IDS_BY_MARKET[market]);
  return [
    ...singleRules,
    ...comboRules,
    ...crossCommon,
    ...crossSpecific,
    ...riskCommon,
    ...riskSpecific,
  ].map((rule): BreadthScreenerRuleMeta => ({
    ...rule,
    tier: coreSet.has(rule.id) ? "core" : baselineSet.has(rule.id) ? "baseline" : "hidden",
  }));
}

export const BREADTH_SCREENER_RULES: readonly BreadthScreenerRuleMeta[] =
  buildScreenerRuleSpecs("cn", "50");

function isLow50(
  index: number,
  b50Arr: readonly (number | null)[],
  dates: readonly string[],
  readings: ReadonlyMap<string, BreadthReadingPoint>,
  cold: number,
): boolean {
  const v50 = b50Arr[index];
  if (!finite(v50)) return false;
  if (v50 <= cold) return true;
  const r50 = readings.get(dates[index])?.horizons?.["50"];
  return r50?.status === "ready" && (r50.position === "low" || (finite(r50.lower) && v50 <= r50.lower));
}

function evalRuleAtIndex(
  ruleId: string,
  index: number,
  market: BreadthScreenerMarket,
  horizon: BreadthHorizon,
  dates: readonly string[],
  prices: readonly (number | null)[],
  b20Arr: readonly (number | null)[],
  b50Arr: readonly (number | null)[],
  b200Arr: readonly (number | null)[],
  readings: ReadonlyMap<string, BreadthReadingPoint>,
  alignedErp: readonly (AlignedErpPoint | null)[],
  alignedMacro: readonly AlignedMacroPoint[],
): boolean {
  const cold = market === "cn" ? 20 : 15;
  const hot = market === "cn" ? 80 : 85;
  const pullbackCold = market === "cn" ? 22 : 18;
  const zweigHigh = market === "cn" ? 75 : 80;
  const deemerBase = market === "cn" ? 30 : 28;

  const b20 = b20Arr[index];
  const b50 = b50Arr[index];
  const b200 = b200Arr[index];
  const price = prices[index];
  const reading = readings.get(dates[index]);
  const erp = alignedErp[index];
  const macro = alignedMacro[index];
  const focusArr = horizon === "20" ? b20Arr : horizon === "200" ? b200Arr : b50Arr;
  const focusVal = focusArr[index];
  const focusReading = reading?.horizons?.[horizon];

  switch (ruleId) {
    case "hist_low": {
      if (!finite(focusVal) || focusReading?.status !== "ready") return false;
      if (focusReading.position === "low") return true;
      return finite(focusReading.lower)
        && finite(focusReading.upper)
        && focusReading.lower < focusReading.upper
        && focusVal <= focusReading.lower;
    }
    case "hist_high": {
      if (!finite(focusVal) || focusReading?.status !== "ready") return false;
      if (focusReading.position === "high") return true;
      return finite(focusReading.lower)
        && finite(focusReading.upper)
        && focusReading.lower < focusReading.upper
        && focusVal >= focusReading.upper;
    }
    case "stage_bottom":
      return finite(b50) && b50 <= cold;
    case "stage_top":
      return finite(b50) && b50 >= hot;
    case "bull_base":
      return finite(b200) && b200 > 50;
    case "bear_base":
      return finite(b200) && b200 < 50;
    case "reversal_bottom":
      return finite(b50) && finite(b200) && b50 <= cold && b200 <= cold;
    case "dual_low_w3": {
      if (!finite(price) || !finite(macro?.priceMa50) || price <= macro.priceMa50) return false;
      const start = Math.max(0, index - 30);
      for (let j = start; j <= index; j++) {
        if (finite(b50Arr[j]) && finite(b200Arr[j]) && b50Arr[j]! <= cold && b200Arr[j]! <= cold) {
          return true;
        }
      }
      return false;
    }
    case "erp_cheap_w3": {
      if (!finite(erp?.z) || erp.z < 1.0 || !finite(price) || !finite(macro?.priceMa50) || price <= macro.priceMa50) {
        return false;
      }
      const start = Math.max(0, index - 30);
      for (let j = start; j <= index; j++) {
        if (isLow50(j, b50Arr, dates, readings, cold)) return true;
      }
      return false;
    }
    case "climax_ma20_break": {
      if (!finite(price) || !finite(macro?.priceMa20) || price >= macro.priceMa20 || !finite(b50) || b50 >= 50) {
        return false;
      }
      const start = Math.max(0, index - 30);
      for (let j = start; j < index; j++) {
        if (finite(b50Arr[j]) && b50Arr[j]! >= hot) return true;
      }
      return false;
    }
    case "weak_base_rally_fade": {
      if (
        !finite(price)
        || !finite(macro?.priceMa20)
        || price >= macro.priceMa20
        || !finite(b200)
        || b200 >= 50
        || !finite(b20)
        || b20 >= 50
      ) {
        return false;
      }
      const start = Math.max(0, index - 10);
      for (let j = start; j < index; j++) {
        if (finite(b20Arr[j]) && b20Arr[j]! >= 70) return true;
      }
      return false;
    }
    case "dual_low_turn": {
      if (
        index < 5
        || !finite(b20)
        || !finite(b50)
        || !finite(b20Arr[index - 5])
        || !finite(b50Arr[index - 5])
      ) {
        return false;
      }
      if (!(b20 > b50 && b20 - b20Arr[index - 5]! >= 8 && b50 > b50Arr[index - 5]!)) return false;
      const start = Math.max(0, index - 15);
      for (let j = start; j <= index; j++) {
        if (finite(b50Arr[j]) && finite(b200Arr[j]) && b50Arr[j]! <= cold && b200Arr[j]! <= cold) {
          return true;
        }
      }
      return false;
    }
    case "reversal_top":
      return finite(b50) && finite(b200) && b50 >= hot && b200 >= hot;
    case "bull_pullback":
      return finite(b200) && finite(b20) && b200 > 50 && b20 <= cold;
    case "bull_pullback_turn": {
      if (index < 1 || !finite(b200) || b200 <= 50 || !finite(b20) || !finite(b20Arr[index - 1])) {
        return false;
      }
      if (b20 <= b20Arr[index - 1]!) return false;
      const start = Math.max(0, index - 5);
      for (let j = start; j <= index; j++) {
        if (finite(b20Arr[j]) && b20Arr[j]! <= pullbackCold) return true;
      }
      return false;
    }
    case "zweig_thrust": {
      if (index < 3 || !finite(b20) || b20 < zweigHigh) return false;
      const start = Math.max(0, index - 12);
      for (let j = start; j < index; j++) {
        if (finite(b20Arr[j]) && b20Arr[j]! <= 20) return true;
      }
      return false;
    }
    case "deemer_thrust": {
      if (index < 10 || !finite(b50) || !finite(b50Arr[index - 10])) return false;
      return b50Arr[index - 10]! <= deemerBase && b50 - b50Arr[index - 10]! >= 25;
    }
    case "washout_thrust": {
      if (index < 5 || !finite(b20) || !finite(b50) || !finite(b20Arr[index - 5])) return false;
      if (!(b20 > b50 && b20 - b20Arr[index - 5]! >= 10)) return false;
      const start = Math.max(0, index - 10);
      for (let j = start; j < index; j++) {
        if (finite(b20Arr[j]) && b20Arr[j]! <= cold && isLow50(j, b50Arr, dates, readings, cold)) {
          return true;
        }
      }
      return false;
    }
    case "top_divergence": {
      if (index < 20 || !finite(price) || !finite(b50) || !finite(b50Arr[index - 20])) return false;
      if (b50 >= 50 || b50 - b50Arr[index - 20]! > -8) return false;
      const winStart = Math.max(0, index - 59);
      let validPriceCount = 0;
      let maxPrice = -Infinity;
      for (let j = winStart; j <= index; j++) {
        const p = prices[j];
        if (finite(p)) {
          validPriceCount++;
          if (p > maxPrice) maxPrice = p;
        }
      }
      return validPriceCount >= 20 && price >= maxPrice * 0.98;
    }
    case "hot_retreat_break": {
      if (
        index < 5
        || !finite(price)
        || !finite(macro?.priceMa20)
        || price >= macro.priceMa20
        || !finite(b50)
        || b50 >= 45
        || !finite(b20)
        || b20 >= 35
      ) {
        return false;
      }
      const start = Math.max(0, index - 20);
      for (let j = start; j < index; j++) {
        if ((finite(b50Arr[j]) && b50Arr[j]! >= 65) || (finite(b20Arr[j]) && b20Arr[j]! >= 80)) {
          return true;
        }
      }
      return false;
    }
    case "bull_base_break": {
      if (index < 3 || !finite(b200) || b200 >= 48 || !finite(b50) || b50 >= 40 || !finite(b20) || b20 >= 35) {
        return false;
      }
      const start = Math.max(0, index - 20);
      for (let j = start; j < index; j++) {
        if (finite(b200Arr[j]) && b200Arr[j]! >= 50) return true;
      }
      return false;
    }
    case "bear_rally_trap": {
      if (index < 3 || !finite(b200) || b200 >= 35 || !finite(b20) || b20 >= 50) return false;
      const start = Math.max(0, index - 6);
      for (let j = start; j < index; j++) {
        if (finite(b20Arr[j]) && b20Arr[j]! >= 65) return true;
      }
      return false;
    }
    case "erp_cheap_low":
      return finite(erp?.z) && erp.z >= 1.5 && isLow50(index, b50Arr, dates, readings, cold);
    case "erp_cheap_turn": {
      if (index < 5 || !finite(erp?.z) || erp.z < 1.0) return false;
      if (!finite(b20) || !finite(b50) || !finite(b20Arr[index - 5]) || !finite(b50Arr[index - 5])) {
        return false;
      }
      if (!(b20 > b20Arr[index - 5]! && b50 > b50Arr[index - 5]! && b20 >= b50)) return false;
      const start = Math.max(0, index - 15);
      for (let j = start; j <= index; j++) {
        if (isLow50(j, b50Arr, dates, readings, cold)) return true;
      }
      return false;
    }
    case "erp_rich_weak":
      return index >= 5
        && finite(erp?.z)
        && erp.z <= -1.5
        && finite(b50)
        && finite(b50Arr[index - 5])
        && b50 < 50
        && b50 < b50Arr[index - 5]!;
    case "cn_triple_bottom":
      return index >= 5
        && finite(erp?.z)
        && erp.z >= 0.8
        && finite(macro?.marginPercentile)
        && macro.marginPercentile <= 35
        && finite(b20)
        && finite(b50)
        && finite(b20Arr[index - 5])
        && b20 >= b50
        && b20 > b20Arr[index - 5]!;
    case "cn_margin_washout":
      return finite(macro?.marginPercentile)
        && macro.marginPercentile <= 20
        && isLow50(index, b50Arr, dates, readings, cold);
    case "cn_margin_crowded_div":
      return index >= 5
        && finite(macro?.marginPercentile)
        && macro.marginPercentile >= 85
        && finite(b20)
        && finite(b50)
        && finite(b50Arr[index - 5])
        && b20 < b50
        && b50 - b50Arr[index - 5]! <= -5;
    case "us_vix_spike_credit_calm":
      return finite(macro?.vix)
        && macro.vix >= 22
        && finite(macro?.hyOas)
        && macro.hyOas < 4.0
        && finite(b200)
        && b200 > 50
        && (
          (finite(b20) && b20 <= 30)
          || (macro.vix <= 30 && finite(macro?.vixTerm) && macro.vixTerm >= 1.0)
        );
    case "us_vix_panic_unwind": {
      if (index < 3 || !finite(macro?.vix) || !finite(b20) || !finite(b20Arr[index - 3])) return false;
      if (b20 <= b20Arr[index - 3]!) return false;
      const start = Math.max(0, index - 10);
      let peakVix = -Infinity;
      for (let j = start; j <= index; j++) {
        const v = alignedMacro[j]?.vix;
        if (finite(v) && v > peakVix) peakVix = v;
      }
      return peakVix >= 28 && macro.vix <= peakVix * 0.88;
    }
    case "us_vix_term_unwind": {
      if (index < 1 || !finite(macro?.vixTerm) || macro.vixTerm >= 0.98) return false;
      const start = Math.max(0, index - 10);
      for (let j = start; j < index; j++) {
        const vt = alignedMacro[j]?.vixTerm;
        if (finite(vt) && vt >= 1.02) return true;
      }
      return false;
    }
    case "us_credit_contagion": {
      if (!finite(macro?.vix) || macro.vix < 25 || !finite(macro?.hyOas) || !finite(b50) || b50 >= 40) {
        return false;
      }
      if (macro.hyOas >= 4.5) return true;
      const prevOas = index >= 20 ? alignedMacro[index - 20]?.hyOas : null;
      return finite(prevOas) && macro.hyOas - prevOas >= 0.5;
    }
    default:
      return false;
  }
}

function condenseEpisodes(
  flags: readonly boolean[],
  dates: readonly string[],
  prices: readonly (number | null)[],
  rule: BreadthScreenerRuleMeta,
): { ranges: Array<[string, string]>; episodes: ScreenedEpisode[]; dayCount: number } {
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
      const startDate = dates[start];
      const endDate = dates[end];
      if (startDate != null && endDate != null) {
        ranges.push([startDate, endDate]);
        episodes.push({
          id: `${rule.id}:${startDate}:${endDate}`,
          ruleId: rule.id,
          ruleLabel: rule.short,
          intent: rule.intent,
          color: rule.color,
          startDate,
          endDate,
          startIndex: start,
          endIndex: end,
          days: end - start + 1,
          startPrice: finite(prices[start]) ? prices[start]! : null,
        });
      }
      start = null;
    }
  }
  return { ranges, episodes, dayCount };
}

function medianOf(nums: readonly number[]): number | null {
  if (!nums.length) return null;
  const sorted = [...nums].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 1 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

function computeHorizonForward(
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
      const pk = prices[k];
      if (finite(pk) && pk < minP) minP = pk;
    }
    mdds.push(((minP / entry) - 1) * 100);
  }

  const baseRets: number[] = [];
  for (let i = 0; i + horizonBars < n; i++) {
    const p0 = prices[i];
    const p1 = prices[i + horizonBars];
    if (finite(p0) && p0 > 0 && finite(p1)) {
      baseRets.push(((p1 / p0) - 1) * 100);
    }
  }

  const baselineMean = baseRets.length
    ? baseRets.reduce((acc, v) => acc + v, 0) / baseRets.length
    : null;
  const baselineWinRate = baseRets.length
    ? (baseRets.filter((v) => v > 0).length / baseRets.length) * 100
    : null;

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

  const meanReturn = rets.reduce((acc, v) => acc + v, 0) / rets.length;
  const winRate = (rets.filter((v) => v > 0).length / rets.length) * 100;
  const medianReturn = medianOf(rets);
  const avgMaxDrawdown = mdds.reduce((acc, v) => acc + v, 0) / mdds.length;

  return {
    horizonBars,
    sampleCount: rets.length,
    winRate,
    meanReturn,
    medianReturn,
    avgMaxDrawdown,
    baselineWinRate,
    baselineMean,
    edgeMean: baselineMean != null ? meanReturn - baselineMean : null,
  };
}

/**
 * Compute causal episode-entry forward 20D & 60D return statistics on the visible price series.
 * Rapid re-triggers within `cooldownBars` of a prior episode's end are merged so one cluster is counted once.
 */
export function computeEpisodeOutcomeStats(
  episodes: readonly ScreenedEpisode[],
  prices: readonly (number | null)[],
  cooldownBars = 5,
): EpisodeOutcomeSummary {
  if (!episodes.length) {
    return {
      rawEpisodeCount: 0,
      dedupEpisodeCount: 0,
      cooldownBars,
      d20: computeHorizonForward([], prices, 20),
      d60: computeHorizonForward([], prices, 60),
    };
  }
  const sorted = [...episodes].sort((a, b) => a.startIndex - b.startIndex || a.endIndex - b.endIndex);
  const merged: Array<{ startIndex: number; endIndex: number }> = [];
  for (const ep of sorted) {
    const last = merged[merged.length - 1];
    if (last && ep.startIndex - last.endIndex <= cooldownBars) {
      last.endIndex = Math.max(last.endIndex, ep.endIndex);
    } else {
      merged.push({ startIndex: ep.startIndex, endIndex: ep.endIndex });
    }
  }
  const entryIndices = merged.map((m) => m.startIndex);
  return {
    rawEpisodeCount: episodes.length,
    dedupEpisodeCount: merged.length,
    cooldownBars,
    d20: computeHorizonForward(entryIndices, prices, 20),
    d60: computeHorizonForward(entryIndices, prices, 60),
  };
}

export function evaluateBreadthScreener({
  market,
  horizon,
  dates,
  prices,
  breadth,
  readings,
  erpBands,
  activeIds,
  auxSeries,
}: {
  market: BreadthScreenerMarket;
  horizon: BreadthHorizon;
  dates: readonly string[];
  prices: readonly (number | null)[];
  breadth: readonly (readonly (number | null)[])[];
  readings: ReadonlyMap<string, BreadthReadingPoint>;
  erpBands: readonly ErpZBandRow[];
  activeIds: ReadonlySet<string>;
  auxSeries?: BreadthScreenerAuxInputs;
}): ScreenerEvaluation {
  const b20Arr = breadth[0] ?? [];
  const b50Arr = breadth[1] ?? [];
  const b200Arr = breadth[2] ?? [];
  const alignedErp = alignErpZToDates(dates, erpBands);

  const marginVals = alignDailySeriesToDates(dates, auxSeries?.marginRatio, 6);
  const marginPctPts = buildCausalPercentilePoints(auxSeries?.marginRatio, 756, 120);
  const marginPct = alignDailySeriesToDates(dates, marginPctPts, 6);
  const vixVals = alignDailySeriesToDates(dates, auxSeries?.vix, 6);
  const vixTermVals = alignDailySeriesToDates(dates, auxSeries?.vixTerm, 6);
  const hyOasVals = alignDailySeriesToDates(dates, auxSeries?.hyOas, 8);
  const fullMa20Pts = buildCausalSmaPoints(auxSeries?.fullPrice, 20);
  const fullMa50Pts = buildCausalSmaPoints(auxSeries?.fullPrice, 50);
  const fullMa60Pts = buildCausalSmaPoints(auxSeries?.fullPrice, 60);
  const fallbackMa20 = rollingSmaArray(prices, 20);
  const fallbackMa50 = rollingSmaArray(prices, 50);
  const fallbackMa60 = rollingSmaArray(prices, 60);
  const alignedMa20 = fullMa20Pts.length ? alignDailySeriesToDates(dates, fullMa20Pts, 3) : fallbackMa20;
  const alignedMa50 = fullMa50Pts.length ? alignDailySeriesToDates(dates, fullMa50Pts, 3) : fallbackMa50;
  const alignedMa60 = fullMa60Pts.length ? alignDailySeriesToDates(dates, fullMa60Pts, 3) : fallbackMa60;

  const alignedMacro: AlignedMacroPoint[] = dates.map((_, i) => ({
    marginRatio: marginVals[i] ?? null,
    marginPercentile: marginPct[i] ?? null,
    vix: vixVals[i] ?? null,
    vixTerm: vixTermVals[i] ?? null,
    hyOas: hyOasVals[i] ?? null,
    priceMa20: alignedMa20[i] ?? fallbackMa20[i] ?? null,
    priceMa50: alignedMa50[i] ?? fallbackMa50[i] ?? null,
    priceMa60: alignedMa60[i] ?? fallbackMa60[i] ?? null,
  }));

  const rules = buildScreenerRuleSpecs(market, horizon);

  const byRule: Record<string, RuleMatchSummary> = {};
  const bands: HighlightBand[] = [];
  const markers: ScreenerEvaluation["markers"] = [];
  const activeEpisodes: ScreenedEpisode[] = [];

  for (const rule of rules) {
    const flags = dates.map((_, i) =>
      evalRuleAtIndex(
        rule.id,
        i,
        market,
        horizon,
        dates,
        prices,
        b20Arr,
        b50Arr,
        b200Arr,
        readings,
        alignedErp,
        alignedMacro,
      ),
    );
    const { ranges, episodes, dayCount } = condenseEpisodes(flags, dates, prices, rule);
    const isActiveLatest = flags.length > 0 && flags[flags.length - 1];
    byRule[rule.id] = {
      rule,
      episodeCount: episodes.length,
      dayCount,
      isActiveLatest,
      ranges,
      episodes,
    };
    if (activeIds.has(rule.id)) {
      bands.push({
        key: rule.id,
        label: rule.short,
        color: rule.color,
        opacity: rule.opacity,
        ranges,
      });
      activeEpisodes.push(...episodes);
      if (!rule.skipStartMarker) {
        for (const ep of episodes) {
          if (finite(ep.startPrice)) {
            markers.push({
              name: rule.short.split(" ")[0],
              value: [ep.startDate, ep.startPrice],
              ruleId: rule.id,
              episodeId: ep.id,
              itemStyle: { color: rule.color },
              label: { color: rule.color, backgroundColor: "rgba(255,255,255,.94)" },
            });
          }
        }
      }
    }
  }

  activeEpisodes.sort((a, b) => a.startDate.localeCompare(b.startDate));
  const outcome = computeEpisodeOutcomeStats(activeEpisodes, prices, 5);
  const outcomeByIntent: OutcomeByIntentSummary = {
    bull: computeEpisodeOutcomeStats(activeEpisodes.filter((ep) => ep.intent === "bull"), prices, 5),
    risk: computeEpisodeOutcomeStats(activeEpisodes.filter((ep) => ep.intent === "risk"), prices, 5),
    neutral: computeEpisodeOutcomeStats(activeEpisodes.filter((ep) => ep.intent === "neutral"), prices, 5),
  };
  const activeIntents = [...new Set(rules.filter((r) => activeIds.has(r.id)).map((r) => r.intent))];
  const latestActiveRuleIds = rules
    .filter((r) => r.tier !== "hidden" && !r.skipStartMarker && byRule[r.id]?.isActiveLatest)
    .sort((a, b) => (a.tier === "core" ? 0 : 1) - (b.tier === "core" ? 0 : 1))
    .map((r) => r.id);
  return {
    byRule,
    bands,
    markers,
    episodes: activeEpisodes,
    alignedErp,
    alignedMacro,
    outcome,
    outcomeByIntent,
    activeIntents,
    latestActiveRuleIds,
  };
}

function rangesOverlapWithTolerance(
  aStart: string,
  aEnd: string,
  bStart: string,
  bEnd: string,
  toleranceDays: number,
): boolean {
  const aS = Date.parse(`${aStart}T00:00:00Z`) - toleranceDays * 86_400_000;
  const aE = Date.parse(`${aEnd}T00:00:00Z`) + toleranceDays * 86_400_000;
  const bS = Date.parse(`${bStart}T00:00:00Z`);
  const bE = Date.parse(`${bEnd}T00:00:00Z`);
  return aS <= bE && bS <= aE;
}

/** Match ERP episodes against cross-market breadth & macro rules for ErpCrossChart filtering. */
export function classifyErpEpisodesWithBreadth<
  T extends { id: string; kind: "upper" | "lower"; startDate: string; endDate: string },
>({
  episodes,
  market,
  breadthDates,
  breadth,
  readings,
  erpBands,
  auxSeries,
  toleranceDays = 7,
}: {
  episodes: readonly T[];
  market: BreadthScreenerMarket;
  breadthDates: readonly string[];
  breadth: readonly (readonly (number | null)[])[];
  readings: ReadonlyMap<string, BreadthReadingPoint>;
  erpBands: readonly ErpZBandRow[];
  auxSeries?: BreadthScreenerAuxInputs;
  toleranceDays?: number;
}): {
  counts: Record<ErpBreadthCrossFilter, number>;
  matchingByFilter: Record<Exclude<ErpBreadthCrossFilter, "all">, Set<string>>;
} {
  const emptyPrices = breadthDates.map(() => null);
  const macroIds = market === "cn"
    ? ["cn_triple_bottom", "cn_margin_washout"]
    : ["us_vix_panic_unwind", "us_vix_term_unwind"];
  const evalResult = evaluateBreadthScreener({
    market,
    horizon: "50",
    dates: breadthDates,
    prices: emptyPrices,
    breadth,
    readings,
    erpBands,
    auxSeries,
    activeIds: new Set(["erp_cheap_low", "erp_cheap_turn", "erp_rich_weak", ...macroIds]),
  });

  const lowRanges = evalResult.byRule.erp_cheap_low?.ranges ?? [];
  const turnRanges = evalResult.byRule.erp_cheap_turn?.ranges ?? [];
  const weakRanges = evalResult.byRule.erp_rich_weak?.ranges ?? [];
  const macroRanges = macroIds.flatMap((id) => evalResult.byRule[id]?.ranges ?? []);

  const matchingByFilter: Record<Exclude<ErpBreadthCrossFilter, "all">, Set<string>> = {
    cheap_low: new Set(),
    cheap_turn: new Set(),
    macro_bull: new Set(),
    rich_weak: new Set(),
  };

  for (const ep of episodes) {
    if (ep.kind === "upper") {
      if (lowRanges.some(([s, e]) => rangesOverlapWithTolerance(ep.startDate, ep.endDate, s, e, toleranceDays))) {
        matchingByFilter.cheap_low.add(ep.id);
      }
      if (turnRanges.some(([s, e]) => rangesOverlapWithTolerance(ep.startDate, ep.endDate, s, e, toleranceDays))) {
        matchingByFilter.cheap_turn.add(ep.id);
      }
      if (macroRanges.some(([s, e]) => rangesOverlapWithTolerance(ep.startDate, ep.endDate, s, e, toleranceDays))) {
        matchingByFilter.macro_bull.add(ep.id);
      }
    } else if (weakRanges.some(([s, e]) => rangesOverlapWithTolerance(ep.startDate, ep.endDate, s, e, toleranceDays))) {
      matchingByFilter.rich_weak.add(ep.id);
    }
  }

  return {
    counts: {
      all: episodes.length,
      cheap_low: matchingByFilter.cheap_low.size,
      cheap_turn: matchingByFilter.cheap_turn.size,
      macro_bull: matchingByFilter.macro_bull.size,
      rich_weak: matchingByFilter.rich_weak.size,
    },
    matchingByFilter,
  };
}

export type ErpChartRuleMeta = {
  id: string;
  intent: RuleIntent;
  tier: "core" | "baseline";
  short: string;
  formula: string;
  basis: string;
  color: string;
  fill: string;
};

export type ErpAlignedContextPoint = {
  b20: number | null;
  b50: number | null;
  erpValue: number | null;
  erpZ: number | null;
  erpZ1y: number | null;
  marginRatio: number | null;
  marginPercentile: number | null;
  vix: number | null;
  hyOas: number | null;
};

export type ErpChartScreenerEvaluation = {
  rules: ErpChartRuleMeta[];
  byRule: Record<string, {
    rule: ErpChartRuleMeta;
    episodeCount: number;
    dayCount: number;
    isActiveLatest: boolean;
    ranges: Array<[string, string]>;
    episodes: ScreenedEpisode[];
  }>;
  markAreas: Array<[{ xAxis: string; itemStyle: { color: string } }, { xAxis: string }]>;
  episodes: ScreenedEpisode[];
  outcome: EpisodeOutcomeSummary;
  outcomeByIntent: OutcomeByIntentSummary;
  activeIntents: RuleIntent[];
  latestActiveRuleIds: string[];
  contextByDate: Map<string, ErpAlignedContextPoint>;
};

export function buildErpChartRuleSpecs(market: BreadthScreenerMarket): ErpChartRuleMeta[] {
  const core: ErpChartRuleMeta[] = market === "cn"
    ? [
        {
          id: "erp_cheap_w3",
          intent: "bull",
          tier: "core",
          short: "股票便宜+跌透后站上50日线",
          formula: "股债利差 ≥ +1σ（买股比买国债划算），近30天内50日宽度曾跌到 ≤20%，今天指数站上50日均线",
          basis: "股票够便宜 + 前期跌透 + 大盘重新走稳：全史后60日上涨率76.0%(+7.11%)，1993年以来三个年代全部赚钱。",
          color: "#0f766e",
          fill: "rgba(15, 118, 110, 0.24)",
        },
        {
          id: "erp_cheap_low",
          intent: "bull",
          tier: "core",
          short: "股票便宜+长短线跌透",
          formula: "股债利差 ≥ +1.0σ（偏便宜），同时50日与200日宽度都跌到 ≤20%",
          basis: "适合长线慢慢攒筹码的便宜大底（沪深300全史后120日上涨率73.9%、中位涨+10.57%）；怕早买磨底就看左边「+站上50日线」。",
          color: "#246b61",
          fill: "rgba(36, 107, 97, 0.20)",
        },
        {
          id: "erp_below_mean_break",
          intent: "risk",
          tier: "core",
          short: "不算便宜+大涨后破20日线",
          formula: "股债利差低于近3年均值（≤0σ，已不算便宜），近20天短线曾极热（20日≥80%），今天20/50日宽度都跌破50%且指数跌破20日均线",
          basis: "股票没了便宜优势，又遇上大涨退潮跌破20日线：沪深300全史29次后20日平均跌2.98%（跑输平时3.83个百分点），三个年代全部下跌。",
          color: "#b45309",
          fill: "rgba(180, 83, 9, 0.25)",
        },
      ]
    : [
        {
          id: "us_erp_cheap_w3",
          intent: "bull",
          tier: "core",
          short: "估值回暖+跌透后站上50日线",
          formula: "标普股债利差近1年适应 Z ≥ +1.0σ（当前利率环境下相对变划算），近30交易日内50日宽度曾跌到 ≤25%，今日标普站上50日均线",
          basis: "用1年适应Z值避免加息换挡期买点长期失明，叠加跌透后站回50日线确认走稳（标普2006年以来23次，后60日胜率87.0%、均回撤-3.09%；样本内历史观察）。",
          color: "#0f766e",
          fill: "rgba(15, 118, 110, 0.24)",
        },
        {
          id: "us_erp_vix_unwind",
          intent: "bull",
          tier: "core",
          short: "估值回暖+恐慌冲高回落",
          formula: "标普股债利差近1年适应 Z ≥ +1.0σ，同时近10交易日恐慌VIX曾冲上 ≥26、今日较峰值回落 ≥10%",
          basis: "当前利率环境下股票相对美债赔率边际修复，同时期权恐慌峰值开始消退（标普2006年以来19次，后60日胜率78.9%、较基准+3.80pp；样本内历史观察）。",
          color: "#1d5f8a",
          fill: "rgba(29, 95, 138, 0.24)",
        },
        {
          id: "us_erp_rich_weak",
          intent: "risk",
          tier: "core",
          short: "估值偏贵+过热后破50日线",
          formula: "标普股债利差3年 Z ≤ −1.5σ（偏贵），近25交易日短线曾过热（20日宽度 ≥80%），今日标普跌破50日均线",
          basis: "只在估值偏贵且前期普涨过热后真正跌破50日线时预警退潮，避免在50日宽度已跌破45%的回调尾声反指卖飞。",
          color: "#986737",
          fill: "rgba(152, 103, 55, 0.26)",
        },
        {
          id: "us_erp_rich_div",
          intent: "risk",
          tier: "core",
          short: "估值偏贵+宽幅转弱破60日线",
          formula: "标普股债利差3年 Z ≤ −1.5σ（偏贵），近30交易日内50日宽度曾 ≥65%，今日跌破50%且标普跌破60日均线",
          basis: "估值偏贵叠加中期参与面从高位回落并确认跌破60日中期趋势线，过滤掉权重股行情中未破位的过早看空噪音。",
          color: "#a14a3b",
          fill: "rgba(161, 74, 59, 0.25)",
        },
      ];

  const baseline: ErpChartRuleMeta[] = [
    {
      id: "raw_cheap_15",
      intent: "bull",
      tier: "baseline",
      short: "只看偏便宜 ≥+1.5σ",
      formula: "股债利差 ≥ 滚动3年均值 + 1.5倍标准差",
      basis: "只看股债利差这一项算偏便宜；早买可能还会顺势往下磨一磨。",
      color: "#327c72",
      fill: "rgba(50, 124, 114, 0.16)",
    },
    {
      id: "raw_cheap_20",
      intent: "bull",
      tier: "baseline",
      short: "只看极便宜 ≥+2σ",
      formula: "股债利差 ≥ 滚动3年均值 + 2倍标准差",
      basis: "过去3年里最便宜的一档位置。",
      color: "#0f766e",
      fill: "rgba(15, 118, 110, 0.24)",
    },
    {
      id: "raw_rich_15",
      intent: "risk",
      tier: "baseline",
      short: "只看偏贵 ≤−1.5σ",
      formula: "股债利差 ≤ 滚动3年均值 − 1.5倍标准差",
      basis: "只看股债利差算偏贵；大牛市或高利率时常一直偏贵照样涨，别单凭它清仓。",
      color: "#986737",
      fill: "rgba(152, 103, 55, 0.18)",
    },
  ];

  return [...core, ...baseline];
}

export function evaluateErpChartScreener({
  market,
  priceDates,
  prices,
  breadthPoints,
  readings,
  erpBands,
  auxSeries,
  activeIds,
}: {
  market: BreadthScreenerMarket;
  priceDates: readonly string[];
  prices: readonly (number | null)[];
  breadthPoints: readonly { date: string; breadth_20?: number | null; breadth_50?: number | null; breadth_200?: number | null }[];
  readings: ReadonlyMap<string, BreadthReadingPoint>;
  erpBands: readonly ErpZBandRow[];
  auxSeries?: BreadthScreenerAuxInputs;
  activeIds: ReadonlySet<string>;
}): ErpChartScreenerEvaluation {
  const b20Arr = alignDailySeriesToDates(
    priceDates,
    breadthPoints.map((p) => ({ date: p.date, value: finite(p.breadth_20) ? p.breadth_20 : null })),
    6,
  );
  const b50Arr = alignDailySeriesToDates(
    priceDates,
    breadthPoints.map((p) => ({ date: p.date, value: finite(p.breadth_50) ? p.breadth_50 : null })),
    6,
  );
  const b200Arr = alignDailySeriesToDates(
    priceDates,
    breadthPoints.map((p) => ({ date: p.date, value: finite(p.breadth_200) ? p.breadth_200 : null })),
    6,
  );
  const alignedErp = alignErpZToDates(priceDates, erpBands, 10);
  const alignedErp1y = market === "us"
    ? alignErpZToDates(priceDates, buildCausalRollingErpZ(erpBands, 1, 180), 10)
    : alignedErp;
  const marginVals = alignDailySeriesToDates(priceDates, auxSeries?.marginRatio, 6);
  const marginPctPts = buildCausalPercentilePoints(auxSeries?.marginRatio, 756, 120);
  const marginPct = alignDailySeriesToDates(priceDates, marginPctPts, 6);
  const vixVals = alignDailySeriesToDates(priceDates, auxSeries?.vix, 6);
  const hyOasVals = alignDailySeriesToDates(priceDates, auxSeries?.hyOas, 8);
  const erpFullMa20 = buildCausalSmaPoints(auxSeries?.fullPrice, 20);
  const erpFullMa50 = buildCausalSmaPoints(auxSeries?.fullPrice, 50);
  const erpFullMa60 = buildCausalSmaPoints(auxSeries?.fullPrice, 60);
  const erpFallbackMa20 = rollingSmaArray(prices, 20);
  const erpFallbackMa50 = rollingSmaArray(prices, 50);
  const erpFallbackMa60 = rollingSmaArray(prices, 60);
  const priceMa20Arr = erpFullMa20.length ? alignDailySeriesToDates(priceDates, erpFullMa20, 3) : erpFallbackMa20;
  const priceMa50Arr = erpFullMa50.length ? alignDailySeriesToDates(priceDates, erpFullMa50, 3) : erpFallbackMa50;
  const priceMa60Arr = erpFullMa60.length ? alignDailySeriesToDates(priceDates, erpFullMa60, 3) : erpFallbackMa60;

  const contextByDate = new Map<string, ErpAlignedContextPoint>();
  priceDates.forEach((d, idx) => {
    contextByDate.set(d, {
      b20: b20Arr[idx] ?? null,
      b50: b50Arr[idx] ?? null,
      erpValue: alignedErp[idx]?.value ?? null,
      erpZ: alignedErp[idx]?.z ?? null,
      erpZ1y: market === "us" ? (alignedErp1y[idx]?.z ?? null) : null,
      marginRatio: marginVals[idx] ?? null,
      marginPercentile: marginPct[idx] ?? null,
      vix: vixVals[idx] ?? null,
      hyOas: hyOasVals[idx] ?? null,
    });
  });

  const rules = buildErpChartRuleSpecs(market);
  const byRule: ErpChartScreenerEvaluation["byRule"] = {};
  const markAreas: ErpChartScreenerEvaluation["markAreas"] = [];
  const activeEpisodes: ScreenedEpisode[] = [];
  const cold = market === "cn" ? 20 : 25;

  const evalAt = (ruleId: string, i: number): boolean => {
    const z = alignedErp[i]?.z;
    const z1y = alignedErp1y[i]?.z;
    const b20 = b20Arr[i];
    const b50 = b50Arr[i];
    const p = prices[i];
    switch (ruleId) {
      case "raw_cheap_15":
        return finite(z) && z >= 1.5;
      case "raw_cheap_20":
        return finite(z) && z >= 2.0;
      case "raw_rich_15":
        return finite(z) && z <= -1.5;
      case "erp_cheap_low":
        return finite(z)
          && z >= 1.0
          && finite(b50)
          && b50 <= 20
          && (!finite(b200Arr[i]) || b200Arr[i]! <= 20);
      case "erp_cheap_w3": {
        const ma50 = priceMa50Arr[i] ?? erpFallbackMa50[i];
        if (!finite(z) || z < 1.0 || !finite(p) || !finite(ma50) || p <= ma50) return false;
        const start = Math.max(0, i - 30);
        for (let j = start; j <= i; j++) {
          if (isLow50(j, b50Arr, priceDates, readings, 20)) return true;
        }
        return false;
      }
      case "us_erp_cheap_w3": {
        const ma50 = priceMa50Arr[i] ?? erpFallbackMa50[i];
        if (!finite(z1y) || z1y < 1.0 || !finite(p) || !finite(ma50) || p <= ma50) return false;
        const start = Math.max(0, i - 30);
        for (let j = start; j <= i; j++) {
          if (isLow50(j, b50Arr, priceDates, readings, 25)) return true;
        }
        return false;
      }
      case "erp_below_mean_break": {
        const ma20 = priceMa20Arr[i] ?? erpFallbackMa20[i];
        if (
          i < 5
          || !finite(z)
          || z > 0.0
          || !finite(p)
          || !finite(ma20)
          || p >= ma20
          || !finite(b50)
          || b50 >= 50
          || !finite(b20)
          || b20 >= 50
        ) {
          return false;
        }
        const start = Math.max(0, i - 20);
        for (let j = start; j < i; j++) {
          if (finite(b20Arr[j]) && b20Arr[j]! >= 80) return true;
        }
        return false;
      }
      case "erp_cheap_turn":
      case "us_erp_cheap_turn": {
        if (i < 5 || !finite(z) || z < 1.0) return false;
        if (!finite(b20) || !finite(b50) || !finite(b20Arr[i - 5]) || !finite(b50Arr[i - 5])) return false;
        if (!(b20 > b20Arr[i - 5]! && b50 > b50Arr[i - 5]! && b20 >= b50)) return false;
        const start = Math.max(0, i - 15);
        for (let j = start; j <= i; j++) {
          if (isLow50(j, b50Arr, priceDates, readings, cold)) return true;
        }
        return false;
      }
      case "cn_triple_bottom":
        return i >= 5
          && finite(z)
          && z >= 0.8
          && finite(marginPct[i])
          && marginPct[i]! <= 35
          && finite(b20)
          && finite(b50)
          && finite(b20Arr[i - 5])
          && b20 >= b50
          && b20 > b20Arr[i - 5]!;
      case "erp_no_cushion_break": {
        const ma20 = priceMa20Arr[i] ?? erpFallbackMa20[i];
        if (
          i < 5
          || !finite(z)
          || z > 0.5
          || !finite(p)
          || !finite(ma20)
          || p >= ma20
          || !finite(b50)
          || b50 >= 45
          || !finite(b20)
          || b20 >= 35
        ) {
          return false;
        }
        const start = Math.max(0, i - 20);
        for (let j = start; j < i; j++) {
          if ((finite(b50Arr[j]) && b50Arr[j]! >= 65) || (finite(b20Arr[j]) && b20Arr[j]! >= 80)) {
            return true;
          }
        }
        return false;
      }
      case "erp_rich_weak": {
        const ma60 = priceMa60Arr[i] ?? erpFallbackMa60[i];
        if (i < 10 || !finite(z) || z > -0.5 || !finite(p) || !finite(ma60) || p >= ma60 || !finite(b50) || b50 >= 45) {
          return false;
        }
        const start = Math.max(0, i - 30);
        for (let j = start; j < i; j++) {
          if (finite(b50Arr[j]) && b50Arr[j]! >= 60) return true;
        }
        return false;
      }
      case "us_erp_rich_weak": {
        const ma50 = priceMa50Arr[i] ?? erpFallbackMa50[i];
        if (i < 25 || !finite(z) || z > -1.5 || !finite(p) || !finite(ma50) || p >= ma50) return false;
        const start = Math.max(0, i - 25);
        for (let j = start; j < i; j++) {
          if (finite(b20Arr[j]) && b20Arr[j]! >= 80) return true;
        }
        return false;
      }
      case "us_erp_vix_unwind": {
        if (i < 5 || !finite(z1y) || z1y < 1.0 || !finite(vixVals[i])) return false;
        const start = Math.max(0, i - 10);
        let peakVix = -Infinity;
        for (let j = start; j <= i; j++) {
          if (finite(vixVals[j]) && vixVals[j]! > peakVix) peakVix = vixVals[j]!;
        }
        return peakVix >= 26 && vixVals[i]! <= peakVix * 0.90;
      }
      case "us_erp_rich_div": {
        const ma60 = priceMa60Arr[i] ?? erpFallbackMa60[i];
        if (i < 30 || !finite(z) || z > -1.5 || !finite(p) || !finite(ma60) || p >= ma60 || !finite(b50) || b50 >= 50) {
          return false;
        }
        const start = Math.max(0, i - 30);
        for (let j = start; j < i; j++) {
          if (finite(b50Arr[j]) && b50Arr[j]! >= 65) return true;
        }
        return false;
      }
      default:
        return false;
    }
  };

  for (const rule of rules) {
    const asMeta: BreadthScreenerRuleMeta = {
      id: rule.id,
      group: "cross",
      intent: rule.intent,
      tier: rule.tier,
      short: rule.short,
      formula: rule.formula,
      basis: rule.basis,
      color: rule.color,
      opacity: 0.24,
    };
    const flags = priceDates.map((_, i) => evalAt(rule.id, i));
    const { ranges, episodes, dayCount } = condenseEpisodes(flags, priceDates, prices, asMeta);
    const isActiveLatest = flags.length > 0 && flags[flags.length - 1];
    byRule[rule.id] = { rule, episodeCount: episodes.length, dayCount, isActiveLatest, ranges, episodes };

    if (activeIds.has(rule.id)) {
      activeEpisodes.push(...episodes);
      for (const ep of episodes) {
        let vStart = ep.startDate;
        let vEnd = ep.endDate;
        if (ep.endIndex + 1 < priceDates.length) {
          const nextD = priceDates[ep.endIndex + 1];
          if (dayGap(ep.endDate, nextD) <= 10) vEnd = nextD;
        }
        if (vStart === vEnd && ep.startIndex > 0) {
          const prevD = priceDates[ep.startIndex - 1];
          if (dayGap(prevD, ep.startDate) <= 10) vStart = prevD;
        }
        if (vStart < vEnd) {
          markAreas.push([{ xAxis: vStart, itemStyle: { color: rule.fill } }, { xAxis: vEnd }]);
        }
      }
    }
  }

  activeEpisodes.sort((a, b) => a.startDate.localeCompare(b.startDate));
  const outcome = computeEpisodeOutcomeStats(activeEpisodes, prices, 5);
  const outcomeByIntent: OutcomeByIntentSummary = {
    bull: computeEpisodeOutcomeStats(activeEpisodes.filter((ep) => ep.intent === "bull"), prices, 5),
    risk: computeEpisodeOutcomeStats(activeEpisodes.filter((ep) => ep.intent === "risk"), prices, 5),
    neutral: computeEpisodeOutcomeStats(activeEpisodes.filter((ep) => ep.intent === "neutral"), prices, 5),
  };
  const activeIntents = [...new Set(rules.filter((r) => activeIds.has(r.id)).map((r) => r.intent))];
  const latestActiveRuleIds = rules
    .filter((r) => byRule[r.id]?.isActiveLatest)
    .sort((a, b) => (a.tier === "core" ? 0 : 1) - (b.tier === "core" ? 0 : 1))
    .map((r) => r.id);

  return {
    rules,
    byRule,
    markAreas,
    episodes: activeEpisodes,
    outcome,
    outcomeByIntent,
    activeIntents,
    latestActiveRuleIds,
    contextByDate,
  };
}
