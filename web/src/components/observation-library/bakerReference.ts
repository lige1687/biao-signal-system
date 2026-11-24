import type { BakerSeries } from "./metricData";

export type BakerVariant = "orth" | "raw";
export type BakerReferencePoint = { date: string; value: number | null; rawValue?: number | null };
export type BakerReference = {
  /** Descriptive cutoffs from the selected version's full available history, not official thresholds. */
  low: number;
  high: number;
  currentValue: number;
  /** Midrank empirical percentile: (count below + half count equal) / valid count × 100. */
  currentPercentile: number;
  /** Backward-compatible display aliases for the BakerReading component. */
  percentile: number;
  state: "cold" | "middle" | "hot";
  variant: BakerVariant;
  sourceStart: string;
  sourceEnd: string;
  sourceCount: number;
  validCount: number;
  start: string;
  end: string;
  count: number;
};

const finite = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value);

function linearQuantile(sorted: readonly number[], fraction: number): number {
  const position = (sorted.length - 1) * fraction;
  const lower = Math.floor(position);
  const upper = Math.ceil(position);
  return sorted[lower] + (sorted[upper] - sorted[lower]) * (position - lower);
}

/** Compute the full-history reference independently for SENT_ORTH or SENT.
 * Pass the unzoomed source series; zooming the chart must not change these bounds.
 */
export function computeBakerReference(
  input: BakerSeries | readonly BakerReferencePoint[],
  currentValue: number | null,
  variant: BakerVariant = "orth",
): BakerReference | null {
  if (!finite(currentValue)) return null;
  const points = Array.isArray(input) ? input : (input as BakerSeries).series;
  if (points.length < 24) return null;
  const sourceDates = points.map((point) => point.date).filter((date) => typeof date === "string" && date.length > 0).sort();
  if (!sourceDates.length) return null;
  const sorted = points.map((point) => variant === "raw" ? point.rawValue : point.value)
    .filter(finite).sort((a, b) => a - b);
  if (sorted.length < 24 || sorted[0] === sorted[sorted.length - 1]) return null;
  const low = linearQuantile(sorted, 0.2);
  const high = linearQuantile(sorted, 0.8);
  // If ties collapse both quantiles, a three-zone interpretation would be arbitrary.
  if (!(low < high)) return null;
  const below = sorted.filter((value) => value < currentValue).length;
  const equal = sorted.filter((value) => value === currentValue).length;
  const percentile = (below + equal / 2) / sorted.length * 100;
  const sourceStart = sourceDates[0];
  const sourceEnd = sourceDates[sourceDates.length - 1];
  return {
    low, high, currentValue, currentPercentile: percentile, percentile,
    state: currentValue <= low ? "cold" : currentValue >= high ? "hot" : "middle",
    variant, sourceStart, sourceEnd, sourceCount: points.length, validCount: sorted.length,
    start: sourceStart, end: sourceEnd, count: sorted.length,
  };
}

/** UI-friendly alias for an already-selected version's complete points. */
export function bakerReference(points: readonly BakerReferencePoint[], currentValue: number | null): BakerReference | null {
  return computeBakerReference(points, currentValue);
}
