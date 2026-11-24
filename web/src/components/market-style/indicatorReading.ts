import type { Point } from "./marketRiskMetrics";

const finite = (value: number | null | undefined): value is number => typeof value === "number" && Number.isFinite(value);
const validDate = (date: string) => /^\d{4}-\d{2}-\d{2}$/.test(date) && Number.isFinite(Date.parse(`${date}T00:00:00Z`))
  && new Date(`${date}T00:00:00Z`).toISOString().slice(0, 10) === date;

/** Compare with exactly N earlier records. Missing, duplicate or unordered records fail closed. */
export function recentDelta(points: Point[], periods: number) {
  if (!Number.isInteger(periods) || periods < 1 || points.length <= periods) return null;
  const window = points.slice(-(periods + 1));
  if (window.some((point, i) => !validDate(point.date) || !finite(point.value) || i > 0 && point.date <= window[i - 1].date)) return null;
  const previous = window[0] as { date: string; value: number };
  const current = window[window.length - 1] as { date: string; value: number };
  return { previous, current, difference: current.value - previous.value, periods };
}

/** Midrank against the preceding complete window, excluding the current point. */
export function historicalPosition(points: Point[], lookback = 756) {
  if (!Number.isInteger(lookback) || lookback < 1 || points.length <= lookback) return null;
  const window = points.slice(-(lookback + 1));
  if (window.some((point, i) => !validDate(point.date) || !finite(point.value) || i > 0 && point.date <= window[i - 1].date)) return null;
  const current = window[window.length - 1].value as number;
  const prior = window.slice(0, -1).map((point) => point.value as number);
  const below = prior.filter((value) => value < current).length;
  const equal = prior.filter((value) => value === current).length;
  return (below + equal / 2) / lookback * 100;
}
