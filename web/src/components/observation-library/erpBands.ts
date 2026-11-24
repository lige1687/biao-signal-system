import type { MetricPoint } from "./metricData";

export const ERP_BAND_METHOD = {
  label: "3年滚动均值 ± 2σ · 独立参照版",
  source: "国信证券，2025-01-27，第9.4节／图163",
  url: "https://pdf.dfcfw.com/pdf/H3_AP202501271642603267_1.pdf?1738011030000.pdf=",
  definition: "过去3个自然年（不含起日、含当日）的均值与总体标准差；先用完整历史计算，再裁剪图示期间。",
  difference: "参照国信证券的三年轨道方法；公开PE未复现报告的调仓盈利对齐。作者视频窗口未披露，尚非原片逐点复刻。",
} as const;

export type ErpBandPoint = MetricPoint & {
  middle: number | null; upper: number | null; lower: number | null;
  sigma: number | null; z: number | null; n: number;
};

const finite = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value);
function dateValid(date: string): boolean {
  return /^\d{4}-\d{2}-\d{2}$/.test(date) && Number.isFinite(Date.parse(date))
    && new Date(`${date}T00:00:00Z`).toISOString().slice(0, 10) === date;
}
function threeYearsBefore(date: string): string {
  const year = Number(date.slice(0, 4)) - 3;
  const candidate = `${year}${date.slice(4)}`;
  // Calendar-year window: Feb 29 maps to Feb 28 when necessary.
  return dateValid(candidate) ? candidate : `${year}-02-28`;
}

/** Descriptive trailing statistics, never a fitted trading threshold. */
export function erpBands(points: readonly MetricPoint[]): ErpBandPoint[] {
  if (points.some((p, i) => !dateValid(p.date) || (i > 0 && p.date <= points[i - 1].date)
    || (p.value !== null && !finite(p.value)))) throw new Error("股债轨道输入日期或数值无效");
  let start = 0;
  return points.map((p, index) => {
    const cutoff = threeYearsBefore(p.date);
    while (start <= index && points[start].date <= cutoff) start++;
    const window = points.slice(start, index + 1);
    const n = window.filter((row) => finite(row.value)).length;
    const blank = { ...p, middle: null, upper: null, lower: null, sigma: null, z: null, n };
    if (points[0].date > cutoff || n < 2 || n !== window.length || p.value === null) return blank;
    const middle = window.reduce((sum, row) => sum + row.value!, 0) / n;
    const sigma = Math.sqrt(window.reduce((sum, row) => sum + (row.value! - middle) ** 2, 0) / n);
    return { ...p, middle, sigma, upper: middle + 2 * sigma, lower: middle - 2 * sigma,
      z: sigma > 0 ? (p.value - middle) / sigma : null, n };
  });
}

export function erpBandPosition(row: ErpBandPoint | undefined): string {
  if (!row || row.value === null || row.upper === null || row.lower === null || row.middle === null) return "轨道历史不足";
  if (row.sigma === 0) return "窗口内无波动";
  if (row.value >= row.upper) return "达到上轨 · 股票相对便宜";
  if (row.value <= row.lower) return "达到下轨 · 股票相对偏贵";
  return row.value >= row.middle ? "中轨上方" : "中轨下方";
}

export function bandDistance(row: Pick<ErpBandPoint, "value" | "upper" | "lower"> | undefined, edge: "upper" | "lower"): string {
  if (!row || row.value === null || row[edge] === null) return "—";
  const distance = edge === "upper" ? row.upper! - row.value : row.value - row.lower!;
  return distance >= 0 ? `距${edge === "upper" ? "上" : "下"}轨 ${distance.toFixed(2)} 个百分点`
    : `超出${edge === "upper" ? "上" : "下"}轨 ${Math.abs(distance).toFixed(2)} 个百分点`;
}
