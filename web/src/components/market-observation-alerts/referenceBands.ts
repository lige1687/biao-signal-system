export type HistoricalPoint = { date: string; value: number | null };

/** Prior-only empirical observation rails. A missing value breaks the qualified window. */
export function priorReferenceBands(points: HistoricalPoint[], lookback = 756, minimum = lookback, displayCount = 252) {
  const low: (number | null)[] = [];
  const high: (number | null)[] = [];
  const quantile = (sorted: number[], fraction: number) => {
    const position = (sorted.length - 1) * fraction;
    const left = Math.floor(position);
    return sorted[left] + (sorted[Math.ceil(position)] - sorted[left]) * (position - left);
  };
  points.forEach((point, index) => {
    if (index < points.length - displayCount) { low.push(null); high.push(null); return; }
    const prior = points.slice(Math.max(0, index - lookback), index);
    if (!Number.isFinite(Date.parse(point.date)) || !Number.isFinite(point.value) || prior.length < minimum ||
      prior.some((entry, i) => !Number.isFinite(Date.parse(entry.date)) || !Number.isFinite(entry.value) ||
        (i > 0 && entry.date <= prior[i - 1].date)) || (prior.length && point.date <= prior[prior.length - 1].date)) {
      low.push(null); high.push(null); return;
    }
    const sorted = prior.map((entry) => entry.value as number).sort((a, b) => a - b);
    low.push(quantile(sorted, .15));
    high.push(quantile(sorted, .85));
  });
  return { low, high, latest: { low: low[low.length - 1] ?? null, high: high[high.length - 1] ?? null } };
}
