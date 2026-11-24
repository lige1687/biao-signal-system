/** Descriptive calendar alignment only. These rows do not establish when a historical metric was public. */
export type ProjectionFrequency = "daily" | "weekly" | "monthly";

export type ProjectionPrice = { dates: string[]; values: (number | null)[] };
export type ProjectionPoint = { date: string; value: number | null };
export type ProjectionAlignment = {
  dates: string[];
  price: (number | null)[];
  values: (number | null)[];
  priceDates: (string | null)[];
  metricDates: (string | null)[];
};

const empty = (): ProjectionAlignment => ({ dates: [], price: [], values: [], priceDates: [], metricDates: [] });
const numberOrNull = (value: unknown): number | null => typeof value === "number" && Number.isFinite(value) ? value : null;
const dayMs = 86_400_000;

function validDay(date: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) return false;
  const parsed = new Date(`${date}T00:00:00Z`);
  return !Number.isNaN(parsed.getTime()) && parsed.toISOString().slice(0, 10) === date;
}

function monthOf(date: string): string | null {
  if (/^\d{4}-\d{2}$/.test(date)) return validDay(`${date}-01`) ? date : null;
  return validDay(date) ? date.slice(0, 7) : null;
}

function cutoff(endDate: string, years: number | null): string | null {
  if (years === null || !Number.isFinite(years) || years <= 0) return null;
  const end = new Date(`${endDate}T00:00:00Z`);
  const shifted = new Date(end);
  shifted.setUTCFullYear(shifted.getUTCFullYear() - years);
  return shifted.toISOString().slice(0, 10);
}

function priceRows(price: ProjectionPrice): ProjectionPoint[] {
  const byDate = new Map<string, number | null>();
  const length = Math.min(price.dates.length, price.values.length);
  for (let index = 0; index < length; index++) {
    const date = price.dates[index];
    if (validDay(date)) byDate.set(date, numberOrNull(price.values[index]));
  }
  return [...byDate].sort(([a], [b]) => a.localeCompare(b)).map(([date, value]) => ({ date, value }));
}

function metricRows(points: readonly ProjectionPoint[], frequency: ProjectionFrequency): ProjectionPoint[] {
  const byDate = new Map<string, number | null>();
  for (const point of points) {
    const date = point.date;
    if (frequency === "monthly" ? monthOf(date) !== null : validDay(date)) byDate.set(date, numberOrNull(point.value));
  }
  return [...byDate].sort(([a], [b]) => a.localeCompare(b)).map(([date, value]) => ({ date, value }));
}

function append(out: ProjectionAlignment, date: string, price: number | null, value: number | null,
  priceDate: string | null, metricDate: string | null): void {
  out.dates.push(date);
  out.price.push(price);
  out.values.push(value);
  out.priceDates.push(priceDate);
  out.metricDates.push(metricDate);
}

function monthlyAxis(start: string, end: string): string[] {
  const out: string[] = [];
  const cursor = new Date(`${start}-01T00:00:00Z`);
  while (cursor.toISOString().slice(0, 7) <= end) {
    out.push(cursor.toISOString().slice(0, 7));
    cursor.setUTCMonth(cursor.getUTCMonth() + 1);
  }
  return out;
}

/** A final month is closed only if no calendar weekdays remain after its last price row.
 * Exchange holidays are unknown here; treating an ambiguous final month as incomplete is conservative.
 */
function finalPriceMonthClosed(lastDate: string): boolean {
  const cursor = new Date(`${lastDate}T00:00:00Z`);
  const month = cursor.getUTCMonth();
  cursor.setUTCDate(cursor.getUTCDate() + 1);
  while (cursor.getUTCMonth() === month) {
    const weekday = cursor.getUTCDay();
    if (weekday !== 0 && weekday !== 6) return false;
    cursor.setUTCDate(cursor.getUTCDate() + 1);
  }
  return true;
}

export function alignProjection(
  price: ProjectionPrice,
  points: ProjectionPoint[],
  frequency: ProjectionFrequency,
  years: number | null,
): ProjectionAlignment {
  const prices = priceRows(price);
  const metrics = metricRows(points, frequency);
  if (!prices.length || !metrics.length) return empty();
  const out = empty();
  if (frequency === "daily") {
    const metricByDate = new Map(metrics.map((point) => [point.date, point.value]));
    const start = metrics[0].date > prices[0].date ? metrics[0].date : prices[0].date;
    const end = metrics[metrics.length - 1].date < prices[prices.length - 1].date
      ? metrics[metrics.length - 1].date : prices[prices.length - 1].date;
    const rangeStart = cutoff(end, years);
    for (const point of prices) {
      if (point.date < start || point.date > end || (rangeStart && point.date < rangeStart)) continue;
      append(out, point.date, point.value, metricByDate.get(point.date) ?? null,
        point.value === null ? null : point.date, metricByDate.has(point.date) ? point.date : null);
    }
    return out;
  }
  if (frequency === "weekly") {
    const start = prices[0].date;
    const end = metrics[metrics.length - 1].date;
    const rangeStart = cutoff(end, years);
    const validPrices = prices.filter((point) => point.value !== null);
    let cursor = 0;
    let prior: ProjectionPoint | null = null;
    for (const point of metrics) {
      while (cursor < validPrices.length && validPrices[cursor].date <= point.date) {
        prior = validPrices[cursor];
        cursor++;
      }
      if (point.date < start || point.date > end || (rangeStart && point.date < rangeStart)) continue;
      const age = prior ? (Date.parse(`${point.date}T00:00:00Z`) - Date.parse(`${prior.date}T00:00:00Z`)) / dayMs : Infinity;
      const matchedPrice: ProjectionPoint | null = prior !== null && age >= 0 && age <= 6 ? prior : null;
      append(out, point.date, matchedPrice?.value ?? null, point.value,
        matchedPrice?.date ?? null, point.date);
    }
    return out;
  }
  const metricByMonth = new Map<string, ProjectionPoint>();
  for (const point of metrics) {
    const month = monthOf(point.date);
    if (month) metricByMonth.set(month, point);
  }
  const priceByMonth = new Map<string, ProjectionPoint>();
  for (const point of prices) {
    const month = point.date.slice(0, 7);
    // The final observed row defines the month even when its close is explicitly missing.
    // Falling back to an earlier close would mislabel a midmonth value as month-end.
    priceByMonth.set(month, point);
  }
  const firstMetricMonth = metrics[0].date.slice(0, 7);
  const lastMetricMonth = metrics[metrics.length - 1].date.slice(0, 7);
  const firstPriceMonth = prices[0].date.slice(0, 7);
  const lastPriceMonth = prices[prices.length - 1].date.slice(0, 7);
  const start = firstMetricMonth > firstPriceMonth ? firstMetricMonth : firstPriceMonth;
  const end = lastMetricMonth < lastPriceMonth ? lastMetricMonth : lastPriceMonth;
  if (start > end) return out;
  const rangeStart = cutoff(`${end}-01`, years)?.slice(0, 7);
  const finalClosed = finalPriceMonthClosed(prices[prices.length - 1].date);
  for (const month of monthlyAxis(start, end)) {
    if (rangeStart && month < rangeStart) continue;
    const metric = metricByMonth.get(month);
    const pricePoint = priceByMonth.get(month);
    const validPrice = !!pricePoint && pricePoint.value !== null && (month !== lastPriceMonth || finalClosed);
    append(out, month, validPrice ? pricePoint.value : null, metric?.value ?? null,
      validPrice ? pricePoint.date : null, metric?.date ?? null);
  }
  return out;
}
