import { priorReferenceBands } from "../market-observation-alerts/referenceBands";
import { recentDelta } from "./indicatorReading";
import type { Point } from "./marketRiskMetrics";

export const isOasValue = (value: number | null | undefined): value is number =>
  typeof value === "number" && Number.isFinite(value);

function oneYearBefore(isoDate: string) {
  const [year, month, day] = isoDate.split("-").map(Number);
  const lastDay = new Date(Date.UTC(year - 1, month, 0)).getUTCDate();
  return new Date(Date.UTC(year - 1, month - 1, Math.min(day, lastDay))).toISOString().slice(0, 10);
}

function quantile(sorted: number[], fraction: number) {
  const index = (sorted.length - 1) * fraction;
  const left = Math.floor(index);
  return sorted[left] + (sorted[Math.ceil(index)] - sorted[left]) * (index - left);
}

export function hyOasReading(points: Point[]) {
  const validDates = points.every(({ date }, i) => {
    const time = Date.parse(date);
    return Number.isFinite(time) && new Date(time).toISOString().slice(0, 10) === date &&
      (i === 0 || date > points[i - 1].date);
  });
  const observed = validDates ? points.filter((point): point is { date: string; value: number } => isOasValue(point.value)) : [];
  const current = observed[observed.length - 1];
  const prior = observed.slice(0, -1);
  const cutoff = current ? oneYearBefore(current.date) : null;
  const pastYear = cutoff ? prior.filter(({ date }) => date >= cutoff) : [];
  // Require calendar coverage and enough observations for a daily one-year comparison.
  const sortedYear = pastYear.length >= 240 && cutoff && prior[0].date <= cutoff
    ? pastYear.map(({ value }) => value).sort((a, b) => a - b) : [];
  const year = sortedYear.length ? { low: quantile(sortedYear, .2), high: quantile(sortedYear, .8) } : null;
  const [status, basis] = !current ? ["读数待补齐"] : !year ? ["近 1 年资料不足"]
    : current.value > year.high ? ["处近 1 年偏高区", "（突破 1Y 80% 分位）"]
    : current.value < year.low ? ["处近 1 年偏低区", "（低于 1Y 20% 分位）"] : ["处近 1 年中间区"];

  // Preserve the existing 756-observation P15/P85 reference, drawn as of today.
  const { low, high } = priorReferenceBands(observed, 756, 756, 1).latest;
  const band = low !== null && high !== null ? { low: Number(low.toFixed(2)), high: Number(high.toFixed(2)) } : null;
  const history = current && cutoff && prior.length >= 252 && prior[0].date < cutoff ? {
    from: prior[0].date, to: prior[prior.length - 1].date,
    percentile: prior.reduce((rank, { value }) => rank + (value < current.value ? 1 : value === current.value ? .5 : 0), 0) / prior.length * 100,
  } : null;
  const recent = recentDelta(observed, 20);
  const bps = recent ? Math.round(recent.difference * 100) : 0;
  const sign = bps > 0 ? "+" : bps < 0 ? "−" : "";
  const change = recent ? {
    from: recent.previous.date,
    direction: bps > 0 ? "up" : bps < 0 ? "down" : "flat",
    text: `${sign}${Math.abs(bps)} bps（${sign}${(Math.abs(bps) / 100).toFixed(2)}%）`,
  } : null;
  const lastIndex = current ? points.findIndex(({ date }) => date === current.date) : -1;
  const plot = lastIndex >= 0 ? points.slice(Math.max(0, lastIndex - 251), lastIndex + 1) : [];
  return { current, status, basis, year, band, history, change, plot: plot.slice(plot.findIndex(({ value }) => isOasValue(value))) };
}
