import type { MetricPoint } from "./metricData";
import type { ErpBandPoint } from "./erpBands";
import type { ComparedErpEvent } from "./erpComparisonDisplay";
import { withErpSigma, type ErpSigma } from "./erpSensitivity";

const finite = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value);

function validDate(date: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) return false;
  const time = Date.parse(`${date}T00:00:00Z`);
  return Number.isFinite(time) && new Date(time).toISOString().slice(0, 10) === date;
}

function threeYearsBefore(date: string): string {
  const year = Number(date.slice(0, 4)) - 3;
  const candidate = `${year}${date.slice(4)}`;
  return validDate(candidate) ? candidate : `${year}-02-28`;
}

/** US display reference: [date minus 3 calendar years, date), population sigma.
 * 500 complete prior daily records are an engineering coverage guard, not a claim of statistical power.
 */
export function usErpBands(points: readonly MetricPoint[]): ErpBandPoint[] {
  if (points.some((point, index) => !validDate(point.date)
    || (index > 0 && point.date <= points[index - 1].date)
    || (point.value !== null && !finite(point.value)))) {
    throw new Error("美股股债轨道输入日期或数值无效");
  }

  let start = 0;
  return points.map((point, index) => {
    const cutoff = threeYearsBefore(point.date);
    while (start < index && points[start].date < cutoff) start++;
    const window = points.slice(start, index);
    const n = window.filter(row => finite(row.value)).length;
    const blank = { ...point, middle: null, upper: null, lower: null, sigma: null, z: null, n };
    if (points[0].date > cutoff || window.length !== n || n < 500 || point.value === null) return blank;

    const middle = window.reduce((sum, row) => sum + row.value!, 0) / n;
    const sigma = Math.sqrt(window.reduce((sum, row) => sum + (row.value! - middle) ** 2, 0) / n);
    return { ...point, middle, sigma, upper: middle + 2 * sigma, lower: middle - 2 * sigma,
      z: sigma > 0 ? (point.value - middle) / sigma : null, n };
  });
}

/** Distinct 1.5/2-sigma display crossings need adjacent supplied observations at most seven days apart. */
export function usErpEvents(rows: readonly ErpBandPoint[], sigmas: readonly ErpSigma[]): ComparedErpEvent[] {
  return [...new Set(sigmas)].flatMap(sigma => {
    const adjusted = withErpSigma(rows, sigma);
    const events: ComparedErpEvent[] = [];
    let previous: ErpBandPoint | null = null;
    for (const row of adjusted) {
      const valid = row.value !== null && row.middle !== null && row.upper !== null && row.lower !== null
        && finite(row.sigma) && row.sigma > 0
        && [row.value, row.middle, row.upper, row.lower].every(finite);
      if (!valid) { previous = null; continue; }
      const gapDays = previous
        ? (Date.parse(`${row.date}T00:00:00Z`) - Date.parse(`${previous.date}T00:00:00Z`)) / 86_400_000
        : Infinity;
      if (previous && gapDays > 0 && gapDays <= 7) {
        const kind = previous.value! <= previous.upper! && row.value! > row.upper! ? "upper"
          : previous.value! >= previous.lower! && row.value! < row.lower! ? "lower" : null;
        if (kind) events.push({ date: row.date, kind, value: row.value!, upper: row.upper!, middle: row.middle!,
          lower: row.lower!, sigma, id: `${sigma}:${row.date}:${kind}` });
      }
      previous = row;
    }
    return events;
  }).sort((a, b) => a.date.localeCompare(b.date) || a.sigma - b.sigma);
}
