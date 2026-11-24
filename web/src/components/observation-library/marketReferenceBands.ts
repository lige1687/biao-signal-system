/** Descriptive reference windows; valuation is never a trading signal. */
export type ReferencePoint = { date: string; value: number | null };
export type ValuationId = "hs300-pe" | "sp500-cape" | "nasdaq100-pe";
export const isValuationId = (id: string): id is ValuationId =>
  id === "hs300-pe" || id === "sp500-cape" || id === "nasdaq100-pe";

export const VALUATION_SOURCES = {
  "hs300-pe": { source: "乐咕乐股 · 沪深300滚动市盈率", url: "https://legulegu.com/stockdata/hs300-ttm-lyr" },
  "sp500-cape": { source: "Multpl · Shiller CAPE 月表", url: "https://www.multpl.com/shiller-pe/table/by-month" },
  "nasdaq100-pe": { source: "Siblis Research · 纳斯达克100估值", url: "https://siblisresearch.com/data/nasdaq-100-pe-ratio/" },
};
export const NASDAQ_VALUATION_SNAPSHOT = { date: "2026-09", value: 35.09 };

export const CONCENTRATION_REFERENCE = {
  source: "中银证券 · 2026-06-07策略周报",
  url: "https://pdf.dfcfw.com/pdf/H3_AP202606071823340820_1.pdf?1780846143000.pdf=",
};

const monthKey = (date: string) => {
  const match = /^(\d{4})-(0[1-9]|1[0-2])(?:-(?:0[1-9]|[12]\d|3[01]))?$/.exec(date);
  return match ? Number(match[1]) * 12 + Number(match[2]) - 1 : null;
};
const monthLabel = (key: number) => `${Math.floor(key / 12)}-${String(key % 12 + 1).padStart(2, "0")}`;
const isPositive = (value: number | null): value is number => value != null && Number.isFinite(value) && value > 0;

/** Take the last valid same-source value in each calendar month; preserve holes. */
export function valuationMonthlyPoints(points: ReferencePoint[]): ReferencePoint[] {
  const months = new Map<number, ReferencePoint>();
  for (const point of points) {
    const key = monthKey(point.date);
    if (key === null) continue;
    const prev = months.get(key);
    if (!prev || (isPositive(point.value) && (!isPositive(prev.value) || prev.date <= point.date))) {
      months.set(key, isPositive(point.value) ? point : { date: monthLabel(key), value: null });
    }
  }
  if (!months.size) return [];
  const keys = [...months.keys()];
  const first = Math.min(...keys), last = Math.max(...keys);
  return Array.from({ length: last - first + 1 }, (_, i) =>
    months.get(first + i) ?? { date: monthLabel(first + i), value: null });
}

function quantile(sorted: number[], p: number): number {
  const i = (sorted.length - 1) * p, lo = Math.floor(i), w = i - lo;
  return sorted[lo] * (1 - w) + sorted[Math.ceil(i)] * w;
}

type Level = {
  date: string;
  n: number;
  lower: number | null;
  upper: number | null;
  lowExtreme: number | null;
  highExtreme: number | null;
  percentile: number | null;
};
const emptyLevel = (date: string, n: number): Level =>
  ({ date, n, lower: null, upper: null, lowExtreme: null, highExtreme: null, percentile: null });

function rollingLevel(points: ReferencePoint[], index: number, months: number): Level {
  const point = points[index];
  const prior = points.slice(Math.max(0, index - months), index)
    .flatMap(p => isPositive(p.value) ? [p.value] : []).sort((a, b) => a - b);
  const level = emptyLevel(point.date, prior.length);
  // Require a full calendar span and at least 90% valid coverage; never extend the window.
  if (index < months || prior.length < Math.ceil(.9 * months)) return level;
  const value = point.value;
  const percentile = value == null ? null
    : 100 * prior.reduce((sum, v) => sum + (v < value ? 1 : v === value ? .5 : 0), 0) / prior.length;
  return { ...level, percentile, lower: quantile(prior, .2), upper: quantile(prior, .8),
    lowExtreme: quantile(prior, .1), highExtreme: quantile(prior, .9) };
}

export function marketReferenceBands(id: string, points: ReferencePoint[], full = false) {
  if (isValuationId(id)) {
    const monthly = valuationMonthlyPoints(points);
    const last = monthly.length - 1;
    const rows = monthly.map((_, i) => rollingLevel(monthly, i, 120));
    const latest = rows[last];
    const sensitivity = last < 0 ? null : rollingLevel(monthly, last, 180);
    const history = monthly.slice(0, Math.max(0, last)).filter(p => isPositive(p.value));
    const historyValues = history.map(p => p.value!).sort((a, b) => a - b);
    const longHistory = history.length < 24 ? null : { upper: quantile(historyValues, .95), n: history.length,
      start: history[0].date.slice(0, 7), end: history[history.length - 1].date.slice(0, 7), full };
    const value = monthly[last]?.value;
    const position = value == null || latest?.lower == null || latest.upper == null ? null
      : value < latest.lower ? "相对偏低" : value > latest.upper ? "相对偏高" : "位于高低参照之间";
    const end = latest ? monthKey(latest.date)! : null;
    return { kind: "valuation" as const, rows, latest, sensitivity, longHistory, position, unit: "倍",
      lowerLabel: "相对偏低 P20", upperLabel: "相对偏高 P80", lowerShort: "P20", upperShort: "P80",
      source: VALUATION_SOURCES[id],
      coverage: end == null ? "" : `${monthLabel(end - 120)}—${monthLabel(end - 1)}，${latest.n}/120个有效月`,
      meaning: "与该指数自身过去10年的估值相比。",
      detail: "每期只用此前的月度记录；图表显示范围可单独切换。历史位置用于观察估值压力，不表示涨跌概率。",
    };
  }
  if (id !== "turnover-concentration") return null;
  const prior: number[] = [];
  const rows = points.map(point => {
    const valid = point.value !== null && Number.isFinite(point.value);
    const row = { ...emptyLevel(point.date, prior.length), lower: prior.length >= 24 ? quantile(prior, .1) : null,
      upper: prior.length >= 24 ? quantile(prior, .9) : null };
    if (valid) { prior.push(point.value!); prior.sort((a, b) => a - b); }
    return row;
  });
  return { kind: "concentration" as const, rows, latest: rows[rows.length - 1], unit: "%",
    lowerLabel: "低集中 P10", upperLabel: "高集中 P90", lowerShort: "P10", upperShort: "P90",
    source: CONCENTRATION_REFERENCE,
    coverage: `本地${points[0]?.date.slice(0, 7) ?? "—"}起月频参照；此前${rows[rows.length - 1]?.n ?? 0}个有效月份`,
    meaning: "高集中且成交额萎缩时留意拥挤；低集中表示交易分散，不能单独视为机会。",
    detail: "中银证券明确反对机械套用45%变盘线，并要求结合全市场成交额。本图为月度前5%股票成交额占比；P10/P90仅来自此前完整月份的本地分布，非机构买卖线。缺月不计入分布，历史覆盖不连续。",
  };
}

export type ValuationReference = Extract<NonNullable<ReturnType<typeof marketReferenceBands>>, { kind: "valuation" }>;
