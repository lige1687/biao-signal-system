export type Point = { date: string; value: number | null };
export type VolatilityPoint = { date: string; hv20: number | null; hv60: number | null; ratio: number | null };

const finite = (value: number | null | undefined): value is number =>
  typeof value === "number" && Number.isFinite(value);

/** Sample standard deviation of consecutive close-to-close returns, annualized. */
export function historicalVolatility(closes: readonly (number | null)[], end: number, days: number): number | null {
  if (end < days) return null;
  const returns: number[] = [];
  for (let index = end - days + 1; index <= end; index += 1) {
    const previous = closes[index - 1];
    const current = closes[index];
    if (!finite(previous) || !finite(current) || previous <= 0 || current <= 0) return null;
    returns.push(current / previous - 1);
  }
  const mean = returns.reduce((sum, value) => sum + value, 0) / days;
  const variance = returns.reduce((sum, value) => sum + (value - mean) ** 2, 0) / (days - 1);
  return Math.sqrt(variance * 252) * 100;
}

export function volatilityHistory(dates: readonly string[], closes: readonly (number | null)[]): VolatilityPoint[] {
  if (dates.length !== closes.length) return [];
  // Reject a malformed axis rather than annualizing returns across reordered or duplicated observations.
  if (dates.some((date, index) => !/^\d{4}-\d{2}-\d{2}$/.test(date)
    || Number.isNaN(Date.parse(`${date}T00:00:00Z`))
    || new Date(`${date}T00:00:00Z`).toISOString().slice(0, 10) !== date
    || (index > 0 && date <= dates[index - 1]))) return [];
  return dates.map((date, index) => {
    const hv20 = historicalVolatility(closes, index, 20);
    const hv60 = historicalVolatility(closes, index, 60);
    return { date, hv20, hv60, ratio: hv20 !== null && hv60 !== null && hv60 > 0 ? hv20 / hv60 : null };
  });
}

/** Exactly 756 preceding observations; a missing member makes the reference unavailable. */
export function priorVolatilityPercentile(history: readonly VolatilityPoint[], index: number, count = 756): number | null {
  const current = history[index]?.hv20;
  if (current === null || current === undefined || index < count) return null;
  const prior = history.slice(index - count, index).map((point) => point.hv20);
  if (prior.length !== count || prior.some((value) => !finite(value))) return null;
  const below = prior.filter((value) => value! < current).length;
  const equal = prior.filter((value) => value === current).length;
  return (below + equal / 2) / count * 100;
}

export function seriesPoints(series?: { dates: string[]; values: number[] }): Point[] {
  if (!series || series.dates.length !== series.values.length) return [];
  return series.dates.map((date, index) => ({ date, value: finite(series.values[index]) ? series.values[index] : null }));
}
