import { erpBands } from "./erpBands";
import type { MetricPoint } from "./metricData";

export type TrendState = "bull" | "mixed" | "bear";
export const TREND_STATE_NAMES: Record<TrendState, string> = { bull: "偏强", mixed: "分歧／过渡", bear: "偏弱" };

// Frozen research preview; deliberately separate from all production position rules.
export const ERP_RESEARCH_MATRIX = [
  { label: "Z ≤ −1.5", weights: [0, 5, 30] },
  { label: "−1.5 < Z < −1", weights: [0, 20, 50] },
  { label: "−1 ≤ Z < +1.5", weights: [10, 40, 70] },
  { label: "+1.5 ≤ Z < +2", weights: [40, 60, 85] },
  { label: "Z ≥ +2", weights: [70, 85, 100] },
] as const;

export function erpResearchMapping(z: number | null, state: TrendState) {
  if (z == null || !Number.isFinite(z)) return null;
  const column = state === "bear" ? 0 : state === "mixed" ? 1 : 2;
  const row = z <= -1.5 ? 0 : z < -1 ? 1 : z < 1.5 ? 2 : z < 2 ? 3 : 4;
  const knots = [-2, -1.25, 0, 1.75, 2.5];
  const bounded = Math.max(knots[0], Math.min(knots[4], z));
  const upper = Math.max(1, knots.findIndex(value => value >= bounded));
  const fraction = (bounded - knots[upper - 1]) / (knots[upper] - knots[upper - 1]);
  const low = ERP_RESEARCH_MATRIX[upper - 1].weights[column];
  const high = ERP_RESEARCH_MATRIX[upper].weights[column];
  return { row, column, step: ERP_RESEARCH_MATRIX[row].weights[column], continuous: low + fraction * (high - low) };
}

/** Descriptive observations only; these values never enter the production signal engine. */
export function erpPositionObservation(points: readonly MetricPoint[]) {
  const bands = erpBands(points);
  const row = bands[bands.length - 1];
  if (!row || row.value == null || row.middle == null || row.sigma == null) return null;
  // erpBands already enforces the calendar window and complete observations.
  const window = points.slice(-row.n);
  const below = window.filter(point => point.value! < row.value!).length;
  const equal = window.filter(point => point.value === row.value).length;
  return { date: row.date, value: row.value, mean: row.middle, sigma: row.sigma, z: row.z,
    percentile: (below + equal / 2) / row.n * 100, n: row.n };
}

export function erpTrendObservation(prices: readonly MetricPoint[], asOf: string) {
  const rows = prices.filter(point => point.date <= asOf);
  const tail = rows.slice(-125);
  const last = tail[tail.length - 1];
  if (tail.length < 125 || !last || (Date.parse(asOf) - Date.parse(last.date)) / 86_400_000 > 7
    || tail.some((point, i) => point.value == null || !Number.isFinite(point.value) || point.value <= 0
      || (i > 0 && point.date <= tail[i - 1].date))) return null;
  const mean = (length: number, offset = 0) => tail.slice(tail.length - offset - length, tail.length - offset)
    .reduce((sum, point) => sum + point.value!, 0) / length;
  const ma20 = mean(20), ma60 = mean(60), ma120 = mean(120), previous60 = mean(60, 5);
  const price = last.value!;
  const conditions = [price > ma20, ma20 > ma60, ma60 > ma120];
  const score = conditions.filter(Boolean).length;
  const scoreState: TrendState = score === 3 ? "bull" : score === 0 ? "bear" : "mixed";
  const spread = (Math.max(ma20, ma60, ma120) - Math.min(ma20, ma60, ma120)) / ma60;
  const slope = (ma60 / previous60 - 1) * 252 / 5;
  const narrow = spread < .025, flat = Math.abs(slope) <= .05;
  const bandState: TrendState = narrow || flat ? "mixed" : ma20 > ma60 && price > ma20 ? "bull"
    : ma20 < ma60 && price < ma20 ? "bear" : "mixed";
  return { date: last.date, price, ma20, ma60, ma120, score, conditions, scoreState, spread, slope, narrow, flat, bandState };
}
